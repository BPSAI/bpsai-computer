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

### Configuration

Create `~/.bpsai-computer/config.yaml`:

```yaml
operator: mike
workspace: bpsai
workspace_root: C:/Users/mike/PycharmProjects/BPSAI_Workspace
a2a_url: https://a2a.paircoder.ai
poll_interval: 5        # seconds between A2A polls
process_timeout: 1800   # 30 minutes max per dispatch
```

All config values can be overridden via CLI arguments.

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
