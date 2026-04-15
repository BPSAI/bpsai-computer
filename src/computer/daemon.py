"""Dispatch daemon: poll loop + graceful shutdown."""

from __future__ import annotations

import asyncio
import json
import logging
import platform
import re
import shlex
import time
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Awaitable, Callable

from pydantic import ValidationError

from computer.a2a_client import A2AClient
from computer.auth import TokenManager
from computer.ci_collector import CISummaryCollector
from computer.config import DaemonConfig
from computer.contracts.messages import PermissionResponseContent
from computer.dispatcher import DispatchExecutor, DispatchResult, parse_dispatch, parse_resume
from computer.git_collector import GitSummaryCollector
from computer.license_discovery import LicenseDiscoveryError, discover_license_id
from computer.lifecycle import SessionLifecycle, extract_session_id
from computer.scrubber import scrub_credentials
from computer.signal_pusher import SignalPusher
from computer.streamer import OutputStreamer

log = logging.getLogger(__name__)

_EXIT_CODE_RE = re.compile(r"[Ee]xit code (\d+)")
_MAX_PROCESSED_IDS = 10_000


def resolve_license_id(
    config: DaemonConfig, home_dir: Path | None = None,
) -> str:
    """Return license_id from config (if set) or auto-discover from license.json.

    Raises ``LicenseDiscoveryError`` if neither source provides a license_id.
    """
    if config.license_id:
        return config.license_id
    return discover_license_id(home_dir=home_dir)


class Daemon:
    """Main daemon that polls A2A for dispatch messages and executes them."""

    def __init__(self, config: DaemonConfig) -> None:
        self.config = config
        self.running = False
        self._processed_ids: OrderedDict[str, None] = OrderedDict()
        self._pending_permission_requests: set[str] = set()
        self._message_handlers: dict[str, Callable[[dict], Awaitable[None]]] = {}
        self._register_default_handlers()

        # Resolve license_id: config value wins, then auto-discover from file
        license_id: str | None = None
        try:
            license_id = resolve_license_id(config)
        except LicenseDiscoveryError as exc:
            log.warning("License discovery failed: %s", exc)

        token_manager: TokenManager | None = None
        if license_id:
            token_manager = TokenManager(
                paircoder_api_url=config.paircoder_api_url,
                license_id=license_id,
                operator=config.operator,
                org_id=config.org_id,
            )
            log.info("JWT auth enabled: license_id=%s", license_id)
        else:
            log.error("No license_id configured — cannot start daemon without identity")
            raise SystemExit(1)
        self._token_manager = token_manager

        self.a2a = A2AClient(
            base_url=config.a2a_url,
            operator=config.operator,
            workspace=config.workspace,
            token_manager=token_manager,
        )
        self.executor = DispatchExecutor(config)
        self.signal_pusher = SignalPusher(config=config, token_manager=token_manager)
        self.git_collector = GitSummaryCollector(config=config, token_manager=token_manager)
        self.ci_collector = CISummaryCollector(config=config, token_manager=token_manager)
        if not config.a2a_url.startswith("https://"):
            log.warning("a2a_url is not HTTPS: %s — traffic will be unencrypted", config.a2a_url)

    def _register_default_handlers(self) -> None:
        """Register built-in message type handlers."""
        self._message_handlers["dispatch"] = lambda raw: self._process_dispatch(raw)
        self._message_handlers["resume"] = lambda raw: self._process_resume(raw)
        self._message_handlers["permission-response"] = lambda raw: self._process_permission_response(raw)

    def register_message_handler(
        self, message_type: str, handler: Callable[[dict], Awaitable[None]],
    ) -> None:
        """Register a handler for a message type. Replaces any existing handler."""
        self._message_handlers[message_type] = handler

    async def _route_message(self, raw_msg: dict) -> None:
        """Route a message to its registered handler, or ack-and-log if unknown."""
        msg_id = raw_msg.get("id", "")
        if not msg_id:
            log.warning("Skipping message with missing or empty id: %s", raw_msg.get("type", "?"))
            return
        msg_type = raw_msg.get("type", "dispatch")
        handler = self._message_handlers.get(msg_type)
        if handler is not None:
            await handler(raw_msg)
        else:
            msg_id = raw_msg.get("id", "")
            log.warning("Unknown message type %r (id=%s) — acking as unsupported", msg_type, msg_id)
            await self.a2a.ack_message(msg_id, response="unsupported_message_type")

    def shutdown(self) -> None:
        log.info("Shutdown requested")
        self.running = False

    async def _execute_with_lifecycle(
        self,
        message_id: str,
        session_id: str,
        command: str,
        execute_fn: Callable[[OutputStreamer], Awaitable[DispatchResult]],
        resumed: bool = False,
    ) -> tuple[str, DispatchResult]:
        """Run subprocess with streaming, heartbeats, and lifecycle posting."""
        lifecycle = SessionLifecycle(a2a=self.a2a)
        try:
            await lifecycle.post_started(
                session_id=session_id,
                operator=self.config.operator,
                machine=platform.node(),
                workspace=self.config.workspace,
                command=command,
                resumed=resumed,
            )
        except Exception as exc:
            log.error("Lifecycle post_started failed: %s", exc)
            fail_result = DispatchResult(
                message_id=message_id, success=False,
                output=f"Lifecycle startup error: {exc}",
            )
            await self.a2a.post_result(dispatch_id=message_id, content=fail_result.output, success=False)
            return session_id, fail_result

        streamer = OutputStreamer(session_id=session_id, a2a=self.a2a, config=self.config)
        streamer.start()
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        start_time = time.monotonic()
        try:
            result = await execute_fn(streamer)
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            await streamer.stop()
        duration = time.monotonic() - start_time

        real_sid = extract_session_id(getattr(streamer, "stdout_lines", []), fallback_id=session_id)
        await self._post_lifecycle_result(lifecycle, real_sid, result, duration)
        await self.a2a.post_result(dispatch_id=message_id, content=result.output, success=result.success)
        return real_sid, result

    async def _post_lifecycle_result(
        self, lifecycle: SessionLifecycle, session_id: str, result: DispatchResult, duration: float,
    ) -> None:
        """Post session-complete or session-failed lifecycle event."""
        if result.success:
            await lifecycle.post_complete(
                session_id=session_id, exit_code=0,
                duration_seconds=round(duration, 1), output_summary=result.output,
            )
        else:
            is_timeout = "timeout" in result.output.lower()
            m = _EXIT_CODE_RE.search(result.output)
            await lifecycle.post_failed(
                session_id=session_id, error=result.output,
                exit_code=None if is_timeout else (int(m.group(1)) if m else None),
            )

    async def _process_dispatch(self, raw_msg: dict) -> None:
        """Process a single dispatch message: ack, execute, post lifecycle + result."""
        try:
            msg = parse_dispatch(raw_msg)
        except (KeyError, Exception) as exc:
            log.error("Failed to parse dispatch: %s", exc)
            return

        await self.a2a.ack_message(msg.message_id, response="dispatched")
        preliminary_session_id = str(uuid.uuid4())
        command = f"claude -p {shlex.quote(msg.prompt)} --dangerously-skip-permissions"
        command = scrub_credentials(command)
        if len(command) > 1000:
            command = command[:1000] + "... [truncated]"

        session_id, result = await self._execute_with_lifecycle(
            message_id=msg.message_id,
            session_id=preliminary_session_id,
            command=command,
            execute_fn=lambda streamer: self.executor.execute(msg, streamer=streamer),
        )
        log.info("Dispatch %s complete: success=%s session=%s", msg.message_id, result.success, session_id)

    async def _process_resume(self, raw_msg: dict) -> None:
        """Process a single resume message: validate operator, execute --resume, post lifecycle."""
        msg_operator = raw_msg.get("operator", "")
        if not msg_operator or msg_operator != self.config.operator:
            log.warning("Resume operator mismatch: %r != %s", msg_operator, self.config.operator)
            return

        try:
            msg = parse_resume(raw_msg)
        except (KeyError, ValueError, Exception) as exc:
            log.error("Failed to parse resume: %s", exc)
            return

        await self.a2a.ack_message(msg.message_id, response="resuming")
        command = f"claude --resume {msg.session_id} --dangerously-skip-permissions"

        session_id, result = await self._execute_with_lifecycle(
            message_id=msg.message_id,
            session_id=msg.session_id,
            command=command,
            execute_fn=lambda streamer: self.executor.execute_resume(msg, streamer=streamer),
            resumed=True,
        )
        log.info("Resume %s complete: success=%s session=%s", msg.message_id, result.success, session_id)

    async def _process_permission_response(self, raw_msg: dict) -> None:
        """Process a permission-response: validate sender, parse via Pydantic, ack."""
        msg_id = raw_msg.get("id", "")

        # SEC-001: Verify operator matches
        msg_operator = raw_msg.get("operator", "")
        if msg_operator != self.config.operator:
            log.warning(
                "Permission-response operator mismatch: %r != %s (id=%s)",
                msg_operator, self.config.operator, msg_id,
            )
            return

        # SEC-002: Parse content through Pydantic model
        try:
            raw_content = json.loads(raw_msg.get("content", "{}"))
            content = PermissionResponseContent.model_validate(raw_content)
        except (json.JSONDecodeError, ValidationError) as exc:
            log.error("Invalid permission-response content id=%s: %s", msg_id, exc)
            return

        # SEC-001: Verify request_id was pending
        request_id = content.request_id or ""
        if request_id not in self._pending_permission_requests:
            log.warning(
                "Permission-response for unknown request_id=%s (id=%s)",
                request_id, msg_id,
            )
            return
        self._pending_permission_requests.discard(request_id)

        log.info(
            "Permission response id=%s: approved=%s scope=%s ttl=%s request_id=%s",
            msg_id, content.approved, content.scope, content.ttl, request_id,
        )
        await self.a2a.ack_message(msg_id, response="permission-noted")

    async def _heartbeat_loop(self) -> None:
        """Send heartbeats every 30s while a dispatch is running."""
        while True:
            await asyncio.sleep(30)
            await self.a2a.heartbeat()

    async def run(self) -> None:
        """Main loop: poll, dispatch, repeat. Exits when self.running is False."""
        self.running = True
        log.info("Daemon started: operator=%s workspace=%s", self.config.operator, self.config.workspace)
        try:
            while self.running:
                messages = await self.a2a.poll_dispatches()
                for raw_msg in messages:
                    if not self.running:
                        break
                    msg_id = raw_msg.get("id", "")
                    if msg_id in self._processed_ids:
                        continue
                    self._processed_ids[msg_id] = None
                    if len(self._processed_ids) > _MAX_PROCESSED_IDS:
                        self._processed_ids.popitem(last=False)
                    await self._route_message(raw_msg)
                try:
                    await self.signal_pusher.push_signals()
                except Exception as exc:
                    log.warning("Signal push error: %s", exc)
                try:
                    await self.git_collector.push_summaries()
                except Exception as exc:
                    log.warning("Git summary push error: %s", exc)
                try:
                    await self.ci_collector.push_summaries()
                except Exception as exc:
                    log.warning("CI summary push error: %s", exc)
                await asyncio.sleep(self.config.poll_interval)
        except asyncio.CancelledError:
            pass
        finally:
            self.running = False
            await self.a2a.close()
            await self.signal_pusher.close()
            await self.git_collector.close()
            await self.ci_collector.close()
            if self._token_manager:
                await self._token_manager.close()
            log.info("Daemon stopped")
