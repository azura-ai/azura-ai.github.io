import asyncio
from pydantic_ai import Agent

agent = Agent('test')

async def main():
    res = await agent.run('hello')
    print("DIR:", dir(res))

asyncio.run(main())
