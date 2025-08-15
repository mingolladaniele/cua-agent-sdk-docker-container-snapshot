"""CUA Agent + Snapshot Manager Integration Test"""

import asyncio
import logging
import os
import uuid

from dotenv import load_dotenv
from agent import ComputerAgent
from computer import Computer
from snapshot_manager import SnapshotManager, SnapshotTrigger, SnapshotConfig

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def cua_snapshot_test():
    """Test CUA Agent with snapshot comparison"""
    print("\n🧪 CUA Agent + Snapshot Test")
    print("=" * 35)
    
    container_name = f"cua-test-{uuid.uuid4().hex[:8]}"
    config = SnapshotConfig(storage_path="./test_snapshots")
    snapshot_manager = SnapshotManager(config=config)
    
    try:
        print(f"🐳 Creating CUA Computer: {container_name}")
        
        async with Computer(
            os_type="linux",
            provider_type="docker", 
            name=container_name
        ) as computer:
            print("✅ CUA Computer connected")
            
            # Take initial snapshot
            print("📸 Taking initial snapshot...")
            initial_snapshot = await snapshot_manager.create_snapshot(
                container_id=container_name,
                trigger=SnapshotTrigger.MANUAL,
                description="Before agent execution"
            )
            print(f"   Initial snapshot: {initial_snapshot.snapshot_id}")
            
            # Create agent and run task
            agent = ComputerAgent(
                model="anthropic/claude-3-7-sonnet-20250219",
                tools=[computer],
                verbosity=logging.WARNING
            )
            
            print("🚀 Running task: create test.txt file")
            prompt = "Open a terminal and create a file called 'test.txt' with content 'Hello CUA'"
            
            action_count = 0
            async for result in agent.run(prompt):
                if result.get("output"):
                    for item in result["output"]:
                        if item["type"] == "computer_call":
                            action_count += 1
                            print(f"🔧 Action {action_count}: {item['action']['type']}")
            
            print(f"✅ Task completed with {action_count} actions")
            
            # Take final snapshot  
            print("📸 Taking final snapshot...")
            final_snapshot = await snapshot_manager.create_snapshot(
                container_id=container_name,
                trigger=SnapshotTrigger.MANUAL,
                description="After agent execution"
            )
            print(f"   Final snapshot: {final_snapshot.snapshot_id}")
            
            # Verify file was created
            print("🔍 Verifying file creation...")
            result = await asyncio.create_subprocess_exec(
                "docker", "exec", container_name, "cat", "test.txt",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if stdout and b"Hello CUA" in stdout:
                print(f"✅ File verified: '{stdout.decode().strip()}'")
            else:
                print(f"❌ File not found: {stderr.decode().strip() if stderr else 'No output'}")
            
            # Compare snapshots
            print("📊 Snapshot comparison:")
            print(f"   Initial: {initial_snapshot.timestamp.strftime('%H:%M:%S')} - {initial_snapshot.size_bytes:,} bytes")
            print(f"   Final:   {final_snapshot.timestamp.strftime('%H:%M:%S')} - {final_snapshot.size_bytes:,} bytes")
            print(f"   Diff:    {final_snapshot.size_bytes - initial_snapshot.size_bytes:,} bytes added")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Detailed error:")


async def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Need ANTHROPIC_API_KEY in .env file")
        return
    
    try:
        await cua_snapshot_test()
        print("\n✨ Test completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logger.exception("Error details:")


if __name__ == "__main__":
    asyncio.run(main())
