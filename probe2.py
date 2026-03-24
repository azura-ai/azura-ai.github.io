import asyncio
import os
os.environ['GOOGLE_API_KEY']=os.environ.get('GEMINI_API_KEY','test')
from backend.ecommerce_pydantic_bot import ecommerce_agent, CustomerDeps

async def main():
    res = await ecommerce_agent.run('can you check laptop inventory?', deps=CustomerDeps('1',[]))
    print("DIR:", dir(res))
    if hasattr(res, 'data'): print("DATA:", res.data)
    if hasattr(res, 'output'): print("OUTPUT:", res.output)

asyncio.run(main())
