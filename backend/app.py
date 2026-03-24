from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.hospital_bot import agent, PatientDeps
from fastapi.middleware.cors import CORSMiddleware
import os
import sqlite3
import resend
from loguru import logger
from dotenv import load_dotenv

load_dotenv()
# Initialize Database
def init_db():
    conn = sqlite3.connect('nexus.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS submissions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, name TEXT, email TEXT, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# Resend Configuration
resend.api_key = os.getenv("RESEND_API_KEY")

def send_lead_notification(subject: str, html_content: str):
    """Utility to send email notifications for new leads."""
    if not resend.api_key:
        logger.warning("RESEND_API_KEY not set. Skipping email notification.")
        return
    
    try:
        resend.Emails.send({
            "from": "Nexus Intel Leads <onboarding@resend.dev>",
            "to": "kinza99.rj@gmail.com", # Target address requested by user
            "subject": subject,
            "html": html_content
        })
        logger.info(f"Email sent: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

app = FastAPI()

# Configure CORS for GitHub Pages and Local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your GitHub Pages domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# agent is imported from hospital_bot

class ChatRequest(BaseModel):
    patient_id: str = "GUEST"
    patient_name: str = "Visitor"
    message: str

class ContactRequest(BaseModel):
    name: str
    email: str
    message: str

class NewsletterRequest(BaseModel):
    email: str

class ChatResponse(BaseModel):
    response: str

@agent.tool_plain
async def record_lead(name: str, email: str, project_details: str) -> str:
    """Records a new lead's contact information and project interests."""
    logger.info(f"Tool record_lead called: {name}, {email}")
    try:
        conn = sqlite3.connect('nexus.db')
        c = conn.cursor()
        c.execute("INSERT INTO submissions (type, name, email, message) VALUES (?, ?, ?, ?)", 
                  ('chat_lead', name, email, project_details))
        conn.commit()
        conn.close()
        send_lead_notification(
            f"New AI Lead: {name}",
            f"<h3>High-Intent Lead from Chat:</h3>"
            f"<p><strong>Name:</strong> {name}</p>"
            f"<p><strong>Email:</strong> {email}</p>"
            f"<p><strong>Project:</strong> {project_details}</p>"
        )
        return "Success: Lead information has been recorded. Our team will reach out shortly."
    except Exception as e:
        logger.error(f"Tool Error: {e}")
        return "Error: Could not record lead at this time."

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        if not os.getenv("GOOGLE_API_KEY"):
            return ChatResponse(response=f"I'm currently in demo mode. You asked: '{request.message}'. Once the API key is set, I'll provide full intelligent insights!")
            
        deps = PatientDeps(patient_id=request.patient_id, patient_name=request.patient_name)
        result = await agent.run(request.message, deps=deps)
        logger.info(f"Agent response: {result}")
        return ChatResponse(response=str(result.data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/newsletter")
async def subscribe_newsletter(request: NewsletterRequest):
    logger.info(f"New newsletter subscription: {request.email}")
    try:
        conn = sqlite3.connect('nexus.db')
        c = conn.cursor()
        c.execute("INSERT INTO submissions (type, email) VALUES (?, ?)", ('newsletter', request.email))
        conn.commit()
        conn.close()
        send_lead_notification(
            "New Newsletter Subscriber",
            f"<p>New email added to Nexus Intelligence newsletter: <strong>{request.email}</strong></p>"
        )
    except Exception as e:
        logger.error(f"DB Error: {e}")
    return {"status": "success", "message": "Subscribed successfully"}

@app.post("/contact")
async def contact_form(request: ContactRequest):
    logger.info(f"New contact form submission from {request.name} ({request.email}): {request.message}")
    try:
        conn = sqlite3.connect('nexus.db')
        c = conn.cursor()
        c.execute("INSERT INTO submissions (type, name, email, message) VALUES (?, ?, ?, ?)", 
                  ('contact', request.name, request.email, request.message))
        conn.commit()
        conn.close()
        send_lead_notification(
            f"New Contact: {request.name}",
            f"<h3>New Lead from Contact Form:</h3>"
            f"<p><strong>Name:</strong> {request.name}</p>"
            f"<p><strong>Email:</strong> {request.email}</p>"
            f"<p><strong>Message:</strong> {request.message}</p>"
        )
    except Exception as e:
        logger.error(f"DB Error: {e}")
    return {"status": "success", "message": "Message received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
