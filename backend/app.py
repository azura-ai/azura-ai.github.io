from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic_ai import Agent
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Configure CORS for GitHub Pages and Local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your GitHub Pages domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Pydantic AI Agent
agent = Agent(
    'google-gla:gemini-1.5-flash',
    system_prompt=(
        "You are Nexus AI, the intelligent assistant for Nexus Intelligence. "
        "Provide professional, ROI-focused advice on AI/ML/OCR services."
    ),
)

# New Prospector Agent
prospector_agent = Agent(
    'google-gla:gemini-1.5-flash',
    system_prompt=(
        "You are the Nexus Lead Generation Agent. Your job is to identify high-value business prospects "
        "in specific global regions (USA, Europe, Middle East, ANZ) who need AI, OCR, or Automation services. "
        "Based on the region provided, identify real-world industries and potential (simulated or real) companies. "
        "For each prospect, provide: Company Name, Industry, Identified Pain Point, and a Strategic AI Solution."
    ),
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Run the agent (simulated if no API key is provided for now)
        # result = await agent.run(request.message)
        # return ChatResponse(response=result.data)
        
        # Fallback simulation if no API key is set
        if not os.getenv("GEMINI_API_KEY"):
            return ChatResponse(response=f"I'm currently in demo mode. You asked: '{request.message}'. Once the API key is set, I'll provide full intelligent insights!")
            
        result = await agent.run(request.message)
        return ChatResponse(response=str(result.data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/prospects/{region}")
async def get_prospects(region: str):
    try:
        # Use Pydantic AI to dynamically identify leads based on region
        # This simulates a real search/analysis process
        prompt = f"Find 3 high-value prospects for AI/OCR services in {region}. Provide name, industry, pain_point, and solution."
        
        if not os.getenv("GEMINI_API_KEY"):
            # Informative fallback if no key is set
            return [
                {"name": f"Enterprise Corp {region.upper()}", "industry": "Logistics", "pain_point": "Manual data entry", "solution": "OCR Automation"},
                {"name": f"Nexus Partner {region.upper()}", "industry": "Finance", "pain_point": "Fraud detection", "solution": "ML Fraud Engine"}
            ]

        result = await prospector_agent.run(prompt)
        # In a real app, you'd parse this into a list of models.
        # For now, we return it as a structured simulation.
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
