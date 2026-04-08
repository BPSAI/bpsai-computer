# bpsai-computer

Computer₀ dispatch daemon — bridges the Command Center (cloud) and local execution (Claude Code on developer machines or VMs).

## Setup

### Prerequisites

- Python 3.11+
- Claude Code CLI installed and on PATH
- Access to the A2A backend

### Install

```bash
pip install -e ".[dev]"
```

### Install License

The daemon requires a valid license for JWT authentication with the A2A backend.

```bash
# Install your license file (saves to ~/.paircoder/license.json)
bpsai-pair license install /path/to/your-license.json
```

The license file must contain a `payload.license_id` field. The daemon auto-discovers this from `~/.paircoder/license.json` at startup.

To override the license path, set `BPSAI_LICENSE_FILE`:

```bash
export BPSAI_LICENSE_FILE=/custom/path/to/license.json
```

### Configuration

Create `~/.bpsai-computer/config.yaml`:

```yaml
operator: mike            # your operator ID (from portal profile)
workspace: bpsai          # workspace name
workspace_root: /home/mike/workspace   # absolute path to dir containing target repos
a2a_url: https://a2a.paircoder.ai
poll_interval: 5          # seconds between A2A polls
process_timeout: 1800     # 30 minutes max per dispatch
```

All config values can be overridden via CLI arguments.

You can also set `license_id` explicitly in config (useful for cloud VMs where the license file isn't present):

```yaml
license_id: lic-abc-123   # overrides auto-discovery from license.json
```

## Usage

```bash
# Run with config file
bpsai-computer daemon --operator mike --workspace bpsai

# Override config values
bpsai-computer daemon \
  --operator mike \
  --workspace bpsai \
  --workspace-root /home/mike/workspace \
  --a2a-url http://localhost:8000 \
  --poll-interval 3

# Use a custom config file
bpsai-computer daemon --operator mike --workspace bpsai --config /path/to/config.yaml
```

The daemon:
1. Polls the A2A backend for dispatch messages matching its operator + workspace
2. Acknowledges each dispatch immediately
3. Launches Claude Code in the target repo directory
4. Posts the result (with credentials scrubbed) back to A2A
5. Sends heartbeats while executing

Stop with `Ctrl+C` (graceful shutdown on SIGINT/SIGTERM).

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_integration.py -v
```

## Architecture

```
Command Center → A2A Backend → Dispatch Daemon → Claude Code
                                    ↓
                              Posts result → A2A Backend → Activity Feed
```

Each daemon instance is identified by `(operator, workspace)`. Multiple daemons can run simultaneously for different workspaces or operators.

### JWT Authentication Flow

1. At startup, the daemon resolves `license_id` from config or auto-discovers it from `~/.paircoder/license.json`
2. `TokenManager` obtains a JWT from `api.paircoder.ai/api/v1/auth/operator-token` using `license_id` + `operator`
3. The JWT is cached and auto-refreshed on expiry
4. Every A2A request (poll, ack, result post, lifecycle, heartbeat) includes `Authorization: Bearer <token>`
5. If no license is found, the daemon still runs but without JWT auth (A2A calls may fail with 401)
