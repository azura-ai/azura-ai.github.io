import os
import re
import json
import google.generativeai as genai
from datetime import datetime

# Configuration
TOPICS_FILE = 'content_calendar.md'
BLOGS_DIR = 'blogs'
GENAI_API_KEY = os.getenv('GEMINI_API_KEY')

# Company context for consistent, authoritative writing
COMPANY_CONTEXT = """
Azura AI is a specialized AI automation agency serving European enterprises.
We bridge the gap between legacy infrastructure and agentic AI.
Our expertise:
- Intelligent Document Processing (IDP) with Pydantic AI and LangGraph.
- High-precision OCR extraction for Healthcare, Fintech, and Logistics.
- Autonomous agent architectures with human-in-the-loop validation.
- GDPR-compliant AI hosting and private cloud deployments.

Our tech stack: Multi-Agent AI, Python, Pydantic AI, LangGraph, FastAPI, LLMs (Gemini, GPT-4o), Docker.
"""

def get_next_topic():
    """Find the next unwritten topic from the content calendar."""
    with open(TOPICS_FILE, 'r') as f:
        content = f.read()
    
    # Match table rows: | # | **Title** | keyword | intent |
    matches = re.findall(r'\| \d+ \| \*\*([^*]+)\*\* \| ([^|]+) \| ([^|]+) \|', content)
    
    existing_blogs = [f.replace('.md', '') for f in os.listdir(BLOGS_DIR) if f.endswith('.md')]
    
    for title, keyword, intent in matches:
        slug = title.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug).strip('-')
        if slug not in existing_blogs:
            return title.strip(), keyword.strip(), intent.strip(), slug
            
    return None, None, None, None

def generate_blog_post(title, keyword, intent):
    """Generate a technical tutorial following the TestDriven.io (circa 2020) style."""
    genai.configure(api_key=GENAI_API_KEY)
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    system_prompt = f"""You are a senior technical engineer and content lead at Azura AI.
Your goal is to write a high-fidelity technical tutorial that rivals the quality of sites like TestDriven.io or Real Python.

STYLE GUIDELINES (STRICT ADHERENCE REQUIRED):
1. PERSONA: Objective, technical, and tutorial-focused. Write for developers and technical decision-makers.
2. NO EMOJIS: Absolutely no emojis in the title, headers, or body.
3. NO STYLISTIC FLUFF: No decorative horizontal lines (--- or ***). No repetitive dashes used purely for visual spacing.
4. TONE: Objective and authoritative. Avoid marketing fluff like "supercharge," "unlock," or "game-changer."
5. CLARITY: Use standard Markdown headings (## and ###). Do not use excessive bolding.
6. CODE CONTEXT: Focus on implementation. Code blocks are the most important part of the post.

CONTENT STRUCTURE:
# {title}
> A short, one-sentence subtitle summary starting with a blockquote. (Required for metadata extraction)

## Introduction
State the specific technical problem and the proposed solution. Link to relevant concepts if needed.

## Objectives
By the end of this tutorial, you will:
1. ...
2. ...

## Prerequisites
List necessary tools (e.g., Python 3.12, Docker) with links to their official documentation.

## Implementation / Step-by-Step
Break the technical implementation into logical sections.
- Use Bash blocks for terminal commands ($ mkdir project).
- Use Python blocks (```python) for code.
- Explain *why* certain architectural choices are made (e.g., why use LangGraph's StateGraph over a simple loop).

## Conclusion
A brief summary of what was achieved and a subtle, one-sentence mention of how Azura AI helps enterprises scale these specific types of systems.

COMPANY CONTEXT:
{COMPANY_CONTEXT}
"""

    user_prompt = f"""Write a technical tutorial for Azura AI.
Title: {title}
Target Keyword: {keyword}
Search Intent: {intent}

Formatting Constraints:
- NO EMOJIS.
- NO DECORATIVE HORIZONTAL LINES (except for valid Markdown thematic breaks if absolutely necessary for content separation).
- NO "MARKETING" ADJECTIVES.
- MINIMUM 1500 WORDS.
- AT LEAST TWO DETAILED PYTHON CODE BLOCKS.
- ONE COMPARISON TABLE (e.g., Performance vs. Accuracy or Cost Comparison).

Output ONLY the Markdown content."""

    response = model.generate_content(
        [system_prompt, user_prompt],
        generation_config=genai.GenerationConfig(
            temperature=0.4, # Lower temperature for engineering precision
            max_output_tokens=4096
        )
    )
    return response.text

def main():
    if not GENAI_API_KEY:
        print("❌ Error: GEMINI_API_KEY not found.")
        return

    title, keyword, intent, slug = get_next_topic()
    if not title:
        print("✅ No new topics. Content calendar is up to date.")
        return
        
    print(f"✍️ drafting tutorial: {title}")
    content = generate_blog_post(title, keyword, intent)
    
    # Anti-Spam Check: Fix common AI habits
    content = content.replace("---", "").strip() # Remove excessive lines if some slip through
    # However, YAML or specific breaks might need them. Let's be smart.
    # Re-insert the single H1 if it was lost (unlikely with this prompt)
    if not content.startswith('#'):
        content = f"# {title}\n\n{content}"

    filename = os.path.join(BLOGS_DIR, f"{slug}.md")
    with open(filename, 'w') as f:
        f.write(content)
        
    print(f"✨ Created {filename}")
    os.system('python3 refresh_content.py')

if __name__ == "__main__":
    main()
