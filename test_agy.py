import asyncio
import sys
from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig

def my_custom_tool(x: int) -> int:
    """A custom tool that doubles a number."""
    print(f"\n[Tool Execution] my_custom_tool called with {x}")
    return x * 2

async def main():
    try:
        config = LocalAgentConfig(
            system_instructions="You are a helpful math assistant. You MUST use my_custom_tool to double the number 21.",
            capabilities=CapabilitiesConfig(),
            tools=[my_custom_tool]
        )
        async with Agent(config) as agent:
            response = await agent.chat("What is the result of using my_custom_tool on 21?")
            async for token in response:
                sys.stdout.write(token)
                sys.stdout.flush()
            print()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
