import asyncio
import os
from dotenv import load_dotenv

# Load keys
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY", "test")

# Import Pydantic Bot
from backend.ecommerce_pydantic_bot import ecommerce_agent, CustomerDeps

# Import LangGraph Bot
from backend.ecommerce_langgraph_bot import run_langgraph_bot

async def test_pydantic():
    print("--- Testing Pydantic AI Bot ---")
    deps = CustomerDeps(user_id="U88X", cart=["laptop", "mouse"])
    result = await ecommerce_agent.run("Can you check inventory for a laptop?", deps=deps)
    print("Agent Output:", result.output)

def test_langgraph():
    print("--- Testing LangGraph Bot ---")
    output = run_langgraph_bot(user_id="U88X", message="Can you check inventory for a laptop?")
    print("Agent Output:", output)

async def main():
    try:
        await test_pydantic()
    except Exception as e:
        print("Pydantic Error:", e)
        
    try:
        test_langgraph()
    except Exception as e:
        print("LangGraph Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
