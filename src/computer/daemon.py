"""Dispatch daemon: poll loop + graceful shutdown."""

from __future__ import annotations

import asyncio
import logging
import platform
import re
import time
import uuid
from collections import OrderedDict
from typing import Awaitable, Callable

from computer.a2a_client import A2AClient
from computer.auth import TokenManager
from computer.config import DaemonConfig
from computer.dispatcher import DispatchExecutor, DispatchResult, parse_dispatch, parse_resume
from computer.lifecycle import SessionLifecycle, extract_session_id
from computer.streamer import OutputStreamer

log = logging.getLogger(__name__)

_EXIT_CODE_RE = re.compile(r"[Ee]xit code (\d+)")
_MAX_PROCESSED_IDS = 10_000


class Daemon:
    """Main daemon that polls A2A for dispatch messages and executes them."""

    def __init__(self, config: DaemonConfig) -> None:
        self.config = config
        self.running = False
        self._processed_ids: OrderedDict[str, None] = OrderedDict()

        # Set up JWT auth if license_id is configured
        token_manager: TokenManager | None = None
        if config.license_id:
            token_manager = TokenManager(
                paircoder_api_url=config.paircoder_api_url,
                license_id=config.license_id,
                operator=config.operator,
            )
            log.info("JWT auth enabled: license_id=%s", config.license_id)
        else:
            log.warning("No license_id configured — A2A calls will not include JWT auth")
        self._token_manager = token_manager

        self.a2a = A2AClient(
            base_url=config.a2a_url,
            operator=config.operator,
            workspace=config.workspace,
            token_manager=token_manager,
        )
        self.executor = DispatchExecutor(config)
        if not config.a2a_url.startswith("https://"):
            log.warning("a2a_url is not HTTPS: %s — traffic will be unencrypted", config.a2a_url)

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
        command = f"claude -p '{msg.prompt}' --dangerously-skip-permissions"

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
                    if raw_msg.get("type") == "resume":
                        await self._process_resume(raw_msg)
                    else:
                        await self._process_dispatch(raw_msg)
                await asyncio.sleep(self.config.poll_interval)
        except asyncio.CancelledError:
            pass
        finally:
            self.running = False
            await self.a2a.close()
            if self._token_manager:
                await self._token_manager.close()
            log.info("Daemon stopped")
