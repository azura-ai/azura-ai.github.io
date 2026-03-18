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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
