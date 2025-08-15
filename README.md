# CUA Snapshot Manager

A snapshot-based state management system for the [Cua Agent SDK](https://docs.trycua.com). Automatically capture, store, and restore container states during agent execution to enable rollback, debugging, and state recovery.

## Main Goal

Enable CUA agents to create and restore container snapshots at key execution points, providing:
- **State Recovery**: Roll back to previous container states when needed
- **Debugging**: Capture states before/after critical operations  
- **Reliability**: Recover from failures by restoring known good states
- **Development**: Test agent workflows with consistent starting states

## Main Features

### **Core Functionality (Implemented & Tested)**
- **Docker Container Snapshots**: Uses `docker commit` for efficient state capture
- **Smart Metadata Storage**: JSON-based storage with indexing and statistics
- **Full Lifecycle Management**: Create, list, restore, and delete snapshots
- **Automatic Cleanup**: Configurable retention policies and storage limits
- **Rich Configuration**: Multiple triggers, naming patterns, and limits
- **CLI Interface**: Complete command-line tool for all operations

## Quick Start

### Installation

1. **Clone and setup environment:**
```bash
git clone <repository-url>
cd cua-agent-sdk-docker-container-snapshot
uv sync  # or pip install -e .
```

2. **Verify installation:**
```bash
uv run snapshot-manager --help
```

### Prerequisites
- Docker Desktop running
- Python 3.8+
- A running Docker container to snapshot

## 📖 Basic Usage

### CLI Commands

#### Create a Snapshot
```bash
# Basic snapshot
uv run snapshot-manager create my-container --description "Before risky operation"

# With custom trigger and context
uv run snapshot-manager create my-container \
  --trigger run_start \
  --description "Agent run beginning" \
  --context "initialization"
```

#### List Snapshots
```bash
# List all snapshots
uv run snapshot-manager list

# Filter by container
uv run snapshot-manager list --container my-container

# JSON output for scripts
uv run snapshot-manager list --json-output
```

#### Restore from Snapshot
```bash
# Restore to new container
uv run snapshot-manager restore <snapshot-id> --container-name restored-container

# With custom options
uv run snapshot-manager restore <snapshot-id> \
  --container-name my-app-restored \
  --preserve-networks \
  --preserve-volumes
```

#### Storage Management
```bash
# View storage statistics
uv run snapshot-manager stats

# Clean up old snapshots
uv run snapshot-manager cleanup --max-age-days 7

# Delete specific snapshot
uv run snapshot-manager delete <snapshot-id>
```

#### Container Validation
```bash
# Check if container can be snapshotted
uv run snapshot-manager validate my-container
```

### Programmatic Usage

```python
import asyncio
from snapshot_manager import SnapshotManager, SnapshotTrigger

async def main():
    manager = SnapshotManager()
    
    # Create snapshot
    metadata = await manager.create_snapshot(
        container_id="my-container",
        trigger=SnapshotTrigger.MANUAL,
        description="Pre-deployment state"
    )
    
    # List snapshots
    snapshots = await manager.list_snapshots()
    
    # Restore later
    container_id = await manager.restore_snapshot(metadata.snapshot_id)

asyncio.run(main())
```

## ⚙️ Configuration

Create a configuration file (`snapshot-config.json`):

```json
{
  "triggers": ["run_start", "run_end", "after_action"],
  "storage_path": "./snapshots",
  "max_snapshots_per_container": 10,
  "max_total_snapshots": 100,
  "max_storage_size_gb": 5.0,
  "auto_cleanup_days": 7,
  "naming_pattern": "{container_name}_{trigger}_{timestamp}"
}
```

Use with CLI:
```bash
uv run snapshot-manager --config snapshot-config.json create my-container
```

## 📊 Example Workflow

```bash
# 1. Start a test container
docker run -d --name webapp nginx:alpine

# 2. Create initial snapshot
uv run snapshot-manager create webapp --description "Clean nginx installation"

# 3. Make changes to container
docker exec webapp sh -c "echo 'Hello CUA!' > /usr/share/nginx/html/index.html"

# 4. Create snapshot after changes
uv run snapshot-manager create webapp --description "Added custom content"

# 5. List all snapshots
uv run snapshot-manager list

# 6. Restore to previous state
uv run snapshot-manager restore <first-snapshot-id> --container-name webapp-restored

# 7. Verify restoration worked
docker exec webapp-restored cat /usr/share/nginx/html/index.html  # Should be original nginx page
docker exec webapp cat /usr/share/nginx/html/index.html          # Should be "Hello CUA!"
```

## 🛠️ Development

```bash
# Setup development environment
uv sync

# Run tests
uv run pytest

# Install in development mode
pip install -e .

# Build package
python -m build
```