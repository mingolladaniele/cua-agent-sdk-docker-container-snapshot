# CUA Snapshot Manager

A snapshot-based state management system for the [Cua Agent SDK](https://docs.trycua.com). Automatically capture, store, and restore container states during agent execution to enable rollback, debugging, and state recovery.

## Main Goal

Enable CUA agents to create and restore container snapshots at key execution points, providing:
- **State Recovery**: Roll back to previous container states when needed
- **Debugging**: Capture states before/after critical operations  
- **Reliability**: Recover from failures by restoring known good states
- **Development**: Test agent workflows with consistent starting states

## System Overview

### Core Components

#### 1. **SnapshotManager** - Central Orchestrator
- Coordinates all snapshot operations
- Enforces retention policies and storage limits
- Manages operation conflicts and locking
- Provides unified API for all snapshot operations

#### 2. **DockerSnapshotProvider** - Container Interface
- Uses `docker commit` for efficient container snapshots
- Preserves container configuration for accurate restoration
- Handles Docker image lifecycle management
- Validates container states before operations

#### 3. **FileSystemSnapshotStorage** - Persistence Layer
- JSON-based metadata storage with efficient indexing
- Container-to-snapshot relationship tracking
- Storage statistics and monitoring
- Atomic operations for data consistency

#### 4. **SnapshotCallback** - CUA Agent Integration
- Hooks into CUA Agent SDK lifecycle events
- Configurable trigger policies for automatic snapshots
- Non-blocking operation design
- Automatic container context resolution

#### 5. **CLI Interface** - Management Tool
- Complete command-line interface for all operations
- Human-readable output and JSON export options
- Configuration management and scripting support

### Snapshot Triggers

The system automatically creates snapshots based on configurable triggers:

- **`MANUAL`**: Developer-initiated snapshots
- **`RUN_START`**: Beginning of agent execution
- **`RUN_END`**: End of agent execution  
- **`BEFORE_ACTION`**: Before each agent action (click, type, screenshot, etc.)
- **`AFTER_ACTION`**: After each agent action completes
- **`ON_ERROR`**: When errors occur (planned)
- **`PERIODIC`**: Time-based intervals (planned)

### Data Flow

1. **CUA Agent starts** → Callback triggers `RUN_START` snapshot
2. **Agent decides on action** → Callback triggers `BEFORE_ACTION` snapshot
3. **Agent performs action** → Action executes (click, type, etc.)
4. **Action completes** → Callback triggers `AFTER_ACTION` snapshot
5. **Agent finishes** → Callback triggers `RUN_END` snapshot

## Main Features

### **Core Functionality (Implemented & Tested)**
- **Docker Container Snapshots**: Uses `docker commit` for efficient state capture
- **Smart Metadata Storage**: JSON-based storage with indexing and statistics
- **Full Lifecycle Management**: Create, list, restore, and delete snapshots
- **Automatic Cleanup**: Configurable retention policies and storage limits
- **Rich Configuration**: Multiple triggers, naming patterns, and limits
- **CLI Interface**: Complete command-line tool for all operations

### **CUA Agent SDK Integration**
- **Callback System**: Hooks into agent lifecycle events automatically
- **Configurable Triggers**: Manual, run start/end, before/after actions
- **Pluggable Design**: Enable/disable without code changes
- **Non-Intrusive**: Doesn't break existing agent workflows

## Quick Start

### Installation

```bash
git clone <repository-url>
cd cua-agent-sdk-docker-container-snapshot
uv sync
```

### Prerequisites
- Docker Desktop running
- Python 3.8+
- A running Docker container to snapshot

### Basic Usage

#### CLI Commands

```bash
# Create a snapshot
uv run snapshot-manager create my-container --description "Before risky operation"

# List snapshots
uv run snapshot-manager list

# Restore from snapshot
uv run snapshot-manager restore <snapshot-id> --container-name restored-container

# View storage statistics
uv run snapshot-manager stats

# Clean up old snapshots
uv run snapshot-manager cleanup --max-age-days 7
```

#### CUA Agent Integration

```python
from snapshot_manager import SnapshotCallback, SnapshotConfig, SnapshotTrigger

# Configure snapshot behavior
config = SnapshotConfig(
    triggers=[SnapshotTrigger.RUN_START, SnapshotTrigger.RUN_END],
    max_snapshots_per_container=5,
    storage_path="./agent_snapshots"
)

# Create callback for CUA Agent
snapshot_callback = SnapshotCallback(config=config)

# Integrate with your agent
agent = ComputerAgent(
    model="anthropic/claude-3-5-sonnet-20241022",
    tools=[computer],
    callbacks=[snapshot_callback]  # Add snapshot support
)
```

#### Programmatic Usage

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

## Configuration

### Configuration File (`snapshot-config.json`)

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

### Trigger Configuration Examples

```python
# Development mode - capture everything for debugging
development_config = SnapshotConfig(
    triggers=[
        SnapshotTrigger.RUN_START,
        SnapshotTrigger.BEFORE_ACTION,
        SnapshotTrigger.AFTER_ACTION,
        SnapshotTrigger.RUN_END
    ]
)

# Production mode - minimal overhead
production_config = SnapshotConfig(
    triggers=[SnapshotTrigger.RUN_START, SnapshotTrigger.RUN_END]
)

# Safety mode - always have rollback points
safety_config = SnapshotConfig(
    triggers=[SnapshotTrigger.RUN_START, SnapshotTrigger.BEFORE_ACTION]
)
```

## Example Workflow

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
docker exec webapp-restored cat /usr/share/nginx/html/index.html  # Original page
docker exec webapp cat /usr/share/nginx/html/index.html          # "Hello CUA!"
```

## Storage Structure

```
.snapshots/
├── metadata/
│   ├── snapshot-uuid-1.json  # Individual snapshot metadata
│   ├── snapshot-uuid-2.json
│   └── ...
└── index.json               # Master index for fast queries
```

### Snapshot Metadata Format

```json
{
  "snapshot_id": "uuid",
  "container_id": "docker_container_id", 
  "container_name": "container_name",
  "timestamp": "2025-08-15T09:50:55",
  "trigger": "manual|run_start|run_end|after_action",
  "status": "creating|completed|failed|deleted",
  "image_id": "docker_image_id",
  "image_tag": "cua-snapshot/name:trigger-timestamp", 
  "size_bytes": 8294400,
  "description": "Human readable description",
  "labels": {"key": "value"},
  "agent_metadata": {
    "run_id": "agent_run_id",
    "original_config": "container_configuration",
    "restoration_count": 0
  }
}
```

## Development

```bash
# Setup development environment
uv sync

# Run code formatting
uv run ruff check --fix src/ tests/ examples/
uv run black src/ tests/ examples/
uv run isort src/ tests/ examples/

# Run tests
uv run pytest

# Install in development mode
pip install -e .
```