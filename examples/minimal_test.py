"""
Minimal CUA Agent + Snapshot Manager Integration Test

This creates a very simple test that works around the CUA container naming issue.
"""

import asyncio
import logging
import os
import uuid

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from agent import ComputerAgent
from computer import Computer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def minimal_cua_test():
    """
    Minimal test to verify CUA Agent can create files.
    """
    print("\n🧪 CUA Agent File Creation Test (No Snapshots)")
    print("=" * 50)
    
    try:
        # Generate a valid container name
        container_name = f"cua-test-{uuid.uuid4().hex[:8]}"
        
        print(f"🐳 Creating CUA Computer with container name: {container_name}")
        
        # Try with explicit container name to avoid the naming bug
        async with Computer(
            os_type="linux",
            provider_type="docker",
            name=container_name  # Provide a clean name
        ) as computer:
            
            print("✅ CUA Computer connected successfully!")
            
            # Create minimal agent with Claude (no callbacks for now)
            agent = ComputerAgent(
                model="anthropic/claude-3-7-sonnet-20250219",
                tools=[computer],
                verbosity=logging.WARNING  # Reduce noise
            )
            
            print("✅ Agent created successfully")
            
            # Simple verifiable task - create one file
            prompt = "Open a terminal and create a file called 'test.txt' with content 'Hello CUA'"
            
            print("🚀 Running simple file creation task...")
            
            # Track all actions
            action_count = 0
            
            async for result in agent.run(prompt):
                if result.get("output") and len(result["output"]) > 0:
                    for item in result["output"]:
                        if item["type"] == "message":
                            print(f"🤖 Agent: {item['content'][0]['text']}...")
                        elif item["type"] == "computer_call":
                            action_count += 1
                            action_type = item['action']['type']
                            print(f"🔧 Action {action_count}: {action_type}")
                            
                            # Show key details for certain actions
                            if action_type == "type" and "text" in item['action']:
                                text = item['action']['text']
                                print(f"   Typing: {text}...")
            
            print(f"\n✅ Task completed with {action_count} actions!")
            
            # Verify the file was created
            print("\n🔍 Verifying file creation...")
            try:
                # Check if file exists and has correct content
                result = await asyncio.create_subprocess_exec(
                    "docker", "exec", container_name, "cat", "test.txt",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if stdout and b"Hello CUA" in stdout:
                    print(f"✅ SUCCESS: File created with correct content!")
                    print(f"   Content: '{stdout.decode().strip()}'")
                elif stderr:
                    print(f"❌ File not found: {stderr.decode().strip()}")
                    # Check what files exist in the home directory
                    ls_result = await asyncio.create_subprocess_exec(
                        "docker", "exec", container_name, "ls", "-la",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    ls_stdout, _ = await ls_result.communicate()
                    if ls_stdout:
                        print(f"📁 Files in home directory:\n{ls_stdout.decode()}")
                else:
                    print("❌ No output from file check")
                    
            except Exception as e:
                print(f"❌ File verification error: {e}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Detailed error:")


async def main():
    """Main execution."""
    print("🎯 Minimal CUA Integration Test")
    print("=" * 35)
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Need ANTHROPIC_API_KEY in .env file")
        return
    
    try:
        await minimal_cua_test()
        print("\n✨ Test completed!")
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
    except Exception as e:
        print(f"\n❌ Failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
