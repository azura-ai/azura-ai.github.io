import os
import re
import json
import google.generativeai as genai
from datetime import datetime

# Configuration
CALENDAR_FILE = 'content_calendar.md'
GENAI_API_KEY = os.getenv('GEMINI_API_KEY')

# 2026 Market Intelligence Seeds
TRENDING_MARKET_CONTEXT = """
Current High-Demand Trends (2026):
1. Agentic AI Workflows: AI that doesn't just extract data, but reconciles ERP discrepancies and executes business actions.
2. Healthcare Document Orchestration: Prior authorization automation, clinical note scribing, and supply chain exception management.
3. Fintech Auditability: Streamlining mortgage/loan processing and real-time regulatory compliance (GDPR/HIPAA).
4. LogisticsChain of Custody: Automating customs forms and physical-to-digital reconciliation.
5. Data Readiness: Preparing legacy enterprise data for AI ingestion and layout-aware processing.
"""

def get_existing_topics():
    if not os.path.exists(CALENDAR_FILE):
        return []
    with open(CALENDAR_FILE, 'r') as f:
        content = f.read()
    # Match titles: | # | **Title** | ...
    titles = re.findall(r'\| \d+ \| \*\*([^*]+)\*\* \|', content)
    return [t.strip() for t in titles]

def get_current_id_count():
    if not os.path.exists(CALENDAR_FILE):
        return 0
    with open(CALENDAR_FILE, 'r') as f:
        content = f.read()
    ids = re.findall(r'\| (\d+) \|', content)
    return max([int(i) for i in ids]) if ids else 0

def discover_new_topics(existing_titles):
    genai.configure(api_key=GENAI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""You are a Senior Enterprise SEO Strategist specializing in AI Automation and Document Intelligence.
Your task is to generate 5 NEW, high-authority technical blog post topics for Azura AI.

TRENDING MARKET CONTEXT (2026):
{TRENDING_MARKET_CONTEXT}

CORE NICHE:
Azura AI serves European enterprises in Healthcare, Fintech, and Logistics.
Current Topics (DO NOT REPEAT THESE):
{json.dumps(existing_titles)}

CRITICAL QUALITY GUIDELINES:
1. NO SPAM: Avoid words like "Revolutionize," "Unlock," "Game-changer," "Supercharge."
2. HIGH INTENT: Focus on terms decision-makers search for: "Compliance," "ROI," "Accuracy," "GDPR," "Integration," "Scale."
3. TUTORIAL STYLE: Each title should sound like a deep-dive technical guide (e.g., "Architecting X," "Implementing Y," "The ROI of Z").
4. INDUSTRY DEPTH: Target specific pain points (e.g., "HIPAA-compliant OCR," "Multi-page Invoice Logic," "Real-time KYC Validation").

OUTPUT FORMAT:
Return ONLY a JSON list of objects with the following keys:
- title: The full technical title (no emojis)
- keyword: The primary target search term
- intent: The specific business buyer persona (e.g., "Compliance Lead," "CTO")

Example:
[
  {{"title": "Implementing PII Redaction in Large-Scale Document Workflows", "keyword": "pii redaction document automation", "intent": "Data Privacy Officer"}},
  ...
]
"""
    
    response = model.generate_content(prompt)
    try:
        # Clean potential markdown block formatting
        json_str = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(json_str)
    except Exception as e:
        print(f"❌ Error parsing discovery output: {e}")
        return []

def append_to_calendar(new_topics):
    next_id = get_current_id_count() + 1
    new_rows = []
    
    # Filter for quality/spam just in case
    spam_phrases = ["revolutionize", "unlock", "game-changer", "supercharge", "delve", "leverage"]
    
    for topic in new_topics:
        title = topic['title'].strip()
        keyword = topic['keyword'].strip()
        intent = topic['intent'].strip()
        
        # Anti-spam check
        if any(phrase in title.lower() for phrase in spam_phrases):
            print(f"🚫 Skipping spammy topic: {title}")
            continue
            
        row = f"| {next_id} | **{title}** | {keyword} | {intent} |"
        new_rows.append(row)
        next_id += 1
    
    if new_rows:
        with open(CALENDAR_FILE, 'a') as f:
            f.write("\n" + "\n".join(new_rows))
        return len(new_rows)
    return 0

def main():
    if not GENAI_API_KEY:
        print("❌ Error: GEMINI_API_KEY not found.")
        return

    print("🔍 Researching new enterprise AI topics...")
    existing = get_existing_topics()
    new_topics = discover_new_topics(existing)
    
    if not new_topics:
        print("⚠️ No valid topics discovered.")
        return
        
    added_count = append_to_calendar(new_topics)
    print(f"📝 Successfully added {added_count} high-authority topics to {CALENDAR_FILE}.")

if __name__ == "__main__":
    main()
