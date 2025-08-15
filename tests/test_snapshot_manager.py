"""
Test cases for the snapshot manager system.
"""

import shutil
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import docker
import pytest

from snapshot_manager.manager import SnapshotManager
from snapshot_manager.models import SnapshotConfig, SnapshotStatus, SnapshotTrigger
from snapshot_manager.providers.docker_provider import DockerSnapshotProvider
from snapshot_manager.storage import FileSystemSnapshotStorage


class TestSnapshotManager:
    """Test cases for the SnapshotManager class."""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_docker_client(self):
        """Mock Docker client for testing."""
        mock_client = Mock(spec=docker.DockerClient)
        mock_client.ping.return_value = True

        # Mock container
        mock_container = Mock()
        mock_container.id = "test_container_id"
        mock_container.name = "test_container"
        mock_container.status = "running"
        mock_container.image.id = "test_image_id"
        mock_container.labels = {}
        mock_container.attrs = {
            "Created": "2024-01-01T00:00:00Z",
            "Config": {"Env": [], "WorkingDir": "/app"},
            "Mounts": [],
            "NetworkSettings": {},
        }

        # Mock commit operation
        mock_image = Mock()
        mock_image.id = "snapshot_image_id"
        mock_image.attrs = {"Size": 1024 * 1024 * 100}  # 100MB
        mock_container.commit.return_value = mock_image

        mock_client.containers.get.return_value = mock_container
        mock_client.containers.run.return_value = mock_container
        mock_client.images.get.return_value = mock_image

        return mock_client

    @pytest.fixture
    def snapshot_manager(self, temp_storage, mock_docker_client):
        """Create a SnapshotManager instance for testing."""
        config = SnapshotConfig(
            storage_path=temp_storage, max_snapshots_per_container=3, max_total_snapshots=10
        )

        provider = DockerSnapshotProvider(docker_client=mock_docker_client)
        storage = FileSystemSnapshotStorage(base_path=temp_storage)

        return SnapshotManager(provider=provider, storage=storage, config=config)

    @pytest.mark.asyncio
    async def test_create_snapshot(self, snapshot_manager):
        """Test creating a snapshot."""
        metadata = await snapshot_manager.create_snapshot(
            container_id="test_container",
            trigger=SnapshotTrigger.MANUAL,
            description="Test snapshot",
        )

        assert metadata.snapshot_id is not None
        assert metadata.container_name == "test_container"
        assert metadata.trigger == SnapshotTrigger.MANUAL
        assert metadata.status == SnapshotStatus.COMPLETED
        assert metadata.description == "Test snapshot"

    @pytest.mark.asyncio
    async def test_list_snapshots(self, snapshot_manager):
        """Test listing snapshots."""
        # Create a few snapshots
        await snapshot_manager.create_snapshot("test_container", SnapshotTrigger.MANUAL)
        await snapshot_manager.create_snapshot("test_container", SnapshotTrigger.RUN_START)

        # List all snapshots
        snapshots = await snapshot_manager.list_snapshots()
        assert len(snapshots) == 2

        # List snapshots for specific container
        container_snapshots = await snapshot_manager.list_snapshots(
            container_id="test_container_id"
        )
        assert len(container_snapshots) == 2

    @pytest.mark.asyncio
    async def test_snapshot_limits(self, snapshot_manager):
        """Test that snapshot limits are enforced."""
        # Create snapshots up to the limit
        for i in range(4):  # Limit is 3, so this should trigger cleanup
            await snapshot_manager.create_snapshot(
                "test_container", SnapshotTrigger.MANUAL, description=f"Snapshot {i}"
            )

        # Should only have 3 snapshots due to limit
        snapshots = await snapshot_manager.list_snapshots()
        assert len(snapshots) == 3

    @pytest.mark.asyncio
    async def test_delete_snapshot(self, snapshot_manager):
        """Test deleting a snapshot."""
        # Create a snapshot
        metadata = await snapshot_manager.create_snapshot("test_container", SnapshotTrigger.MANUAL)

        # Verify it exists
        snapshots = await snapshot_manager.list_snapshots()
        assert len(snapshots) == 1

        # Delete it
        await snapshot_manager.delete_snapshot(metadata.snapshot_id)

        # Verify it's gone
        snapshots = await snapshot_manager.list_snapshots()
        assert len(snapshots) == 0

    @pytest.mark.asyncio
    async def test_cleanup_old_snapshots(self, snapshot_manager):
        """Test cleaning up old snapshots."""
        # Create some old snapshots by mocking the timestamp
        with patch("snapshot_manager.models.datetime") as mock_datetime:
            # Create an old snapshot
            old_time = datetime.now() - timedelta(days=10)
            mock_datetime.now.return_value = old_time

            old_metadata = await snapshot_manager.create_snapshot(
                "test_container", SnapshotTrigger.MANUAL
            )
            old_metadata.timestamp = old_time
            await snapshot_manager.storage.update_metadata(old_metadata)

        # Create a recent snapshot
        recent_metadata = await snapshot_manager.create_snapshot(
            "test_container", SnapshotTrigger.MANUAL
        )

        # Cleanup snapshots older than 5 days
        cleanup_count = await snapshot_manager.cleanup_old_snapshots(max_age_days=5)

        assert cleanup_count == 1

        # Verify only recent snapshot remains
        snapshots = await snapshot_manager.list_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0].snapshot_id == recent_metadata.snapshot_id


class TestDockerSnapshotProvider:
    """Test cases for the DockerSnapshotProvider."""

    @pytest.fixture
    def mock_docker_client(self):
        """Mock Docker client."""
        mock_client = Mock(spec=docker.DockerClient)
        mock_client.ping.return_value = True
        return mock_client

    @pytest.fixture
    def docker_provider(self, mock_docker_client):
        """Create a DockerSnapshotProvider for testing."""
        return DockerSnapshotProvider(docker_client=mock_docker_client)

    @pytest.mark.asyncio
    async def test_validate_container_success(self, docker_provider, mock_docker_client):
        """Test successful container validation."""
        # Mock container info
        mock_container = Mock()
        mock_container.id = "test_id"
        mock_container.name = "test_name"
        mock_container.status = "running"
        mock_container.image.id = "test_image"
        mock_container.labels = {}
        mock_container.attrs = {"Created": "2024-01-01", "Config": {}, "Mounts": []}

        mock_docker_client.containers.get.return_value = mock_container

        is_valid = await docker_provider.validate_container("test_container")
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_container_not_found(self, docker_provider, mock_docker_client):
        """Test container validation when container doesn't exist."""
        from docker.errors import NotFound

        mock_docker_client.containers.get.side_effect = NotFound("Container not found")

        is_valid = await docker_provider.validate_container("nonexistent_container")
        assert is_valid is False


class TestFileSystemSnapshotStorage:
    """Test cases for the FileSystemSnapshotStorage."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def storage(self, temp_storage):
        """Create a FileSystemSnapshotStorage instance."""
        return FileSystemSnapshotStorage(base_path=temp_storage)

    @pytest.fixture
    def sample_metadata(self):
        """Create sample snapshot metadata."""
        from snapshot_manager.models import SnapshotMetadata

        return SnapshotMetadata(
            snapshot_id="test-snapshot-123",
            container_id="container-456",
            container_name="test_container",
            trigger=SnapshotTrigger.MANUAL,
            description="Test snapshot",
        )

    @pytest.mark.asyncio
    async def test_save_and_load_metadata(self, storage, sample_metadata):
        """Test saving and loading metadata."""
        # Save metadata
        await storage.save_metadata(sample_metadata)

        # Load it back
        loaded_metadata = await storage.load_metadata(sample_metadata.snapshot_id)

        assert loaded_metadata is not None
        assert loaded_metadata.snapshot_id == sample_metadata.snapshot_id
        assert loaded_metadata.container_id == sample_metadata.container_id
        assert loaded_metadata.trigger == sample_metadata.trigger

    @pytest.mark.asyncio
    async def test_list_snapshots_empty(self, storage):
        """Test listing snapshots when none exist."""
        snapshots = await storage.list_snapshots()
        assert snapshots == []

    @pytest.mark.asyncio
    async def test_delete_metadata(self, storage, sample_metadata):
        """Test deleting metadata."""
        # Save metadata
        await storage.save_metadata(sample_metadata)

        # Verify it exists
        loaded = await storage.load_metadata(sample_metadata.snapshot_id)
        assert loaded is not None

        # Delete it
        await storage.delete_metadata(sample_metadata.snapshot_id)

        # Verify it's gone
        loaded = await storage.load_metadata(sample_metadata.snapshot_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_storage_stats(self, storage, sample_metadata):
        """Test getting storage statistics."""
        # Initially empty
        stats = await storage.get_storage_stats()
        assert stats["total_snapshots"] == 0

        # Add a snapshot
        await storage.save_metadata(sample_metadata)

        # Check stats
        stats = await storage.get_storage_stats()
        assert stats["total_snapshots"] == 1
        assert stats["total_containers"] == 1


class TestSnapshotCallback:
    """Test cases for the SnapshotCallback."""

    @pytest.fixture
    def mock_snapshot_manager(self):
        """Mock SnapshotManager for testing."""
        manager = Mock(spec=SnapshotManager)
        manager.should_create_snapshot = AsyncMock(return_value=True)
        manager.create_snapshot = AsyncMock()
        return manager

    @pytest.fixture
    def snapshot_callback(self, mock_snapshot_manager):
        """Create a SnapshotCallback for testing."""
        from snapshot_manager.callback import SnapshotCallback

        return SnapshotCallback(snapshot_manager=mock_snapshot_manager)

    @pytest.mark.asyncio
    async def test_on_run_start(self, snapshot_callback, mock_snapshot_manager):
        """Test run start callback."""
        kwargs = {"container_id": "test_container"}

        await snapshot_callback.on_run_start(kwargs, [])

        # Should have created a run start snapshot
        mock_snapshot_manager.create_snapshot.assert_called_once()
        call_args = mock_snapshot_manager.create_snapshot.call_args
        assert call_args[1]["trigger"] == SnapshotTrigger.RUN_START
        assert call_args[1]["container_id"] == "test_container"

    @pytest.mark.asyncio
    async def test_on_computer_call_start(self, snapshot_callback, mock_snapshot_manager):
        """Test computer call start callback."""
        item = {"action": {"type": "screenshot"}}

        await snapshot_callback.on_computer_call_start(item)

        # Should have created a before-action snapshot if enabled
        if mock_snapshot_manager.should_create_snapshot.return_value:
            mock_snapshot_manager.create_snapshot.assert_called()

    def test_default_container_resolver(self, snapshot_callback):
        """Test the default container resolver."""
        # Test direct container_id
        kwargs = {"container_id": "test_container"}
        result = snapshot_callback.container_resolver(kwargs)
        assert result == "test_container"

        # Test tools with container_id
        mock_tool = Mock()
        mock_tool.container_id = "tool_container"
        kwargs = {"tools": [mock_tool]}
        result = snapshot_callback.container_resolver(kwargs)
        assert result == "tool_container"

        # Test no container found
        kwargs = {"other_param": "value"}
        result = snapshot_callback.container_resolver(kwargs)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__])
