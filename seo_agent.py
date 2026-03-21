import os
import re
import json
import google.generativeai as genai
from datetime import datetime

# Configuration
TOPICS_FILE = 'vibe_topics.md'
BLOGS_DIR = 'blogs'
GENAI_API_KEY = os.getenv('GEMINI_API_KEY')

def get_next_topic():
    # Load topics from MD table
    with open(TOPICS_FILE, 'r') as f:
        content = f.read()
    
    # Regex to find | # | Topic Title | Focus | ...
    # Matches: | 1 | **Title** | ...
    matches = re.findall(r'\| \d+ \| \*\*([^*]+)\*\* \| ([^|]+) \|', content)
    
    existing_blogs = [f.replace('.md', '') for f in os.listdir(BLOGS_DIR) if f.endswith('.md')]
    
    for title, focus in matches:
        slug = title.lower().replace(' ', '-').replace(':', '').replace('?', '').replace('(', '').replace(')', '').strip()
        if slug not in existing_blogs:
            return title.strip(), focus.strip(), slug
            
    return None, None, None

def generate_blog_post(title, focus):
    genai.configure(api_key=GENAI_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest') # High speed, high vibes
    
    prompt = f"""
    You are a world-class technical SEO writer specializing in the "Vibe Coding" movement.
    Write a high-quality, 1000-word blog post in Markdown format.
    
    Topic: {title}
    Primary Focus: {focus}
    Audience: Vibe Coders (Advanced developers who prioritize high-level intent, AI-assistance, and rapid orchestration).
    Stack: Python, Pydantic AI, Gemini API, LangGraph, FastAPI.
    
    Structure:
    1. H1 Title (The one provided)
    2. > One-line subtitle for SEO injection.
    3. Introduction: What is the "Vibe" of this topic? Why does it matter in 2026?
    4. Technical Deep Dive: 3-4 Detailed sections with code snippets (Python).
    5. Comparison/Insight: How does this fit into the broader AI agent ecosystem?
    6. Practical "Vibe Check": A summary of how to implement this TODAY.
    7. Conclusion with a call-to-action to Nexus Intelligence for custom Document Workflow Automation.
    
    Style: Technical, authoritative, yet modern and "vibe-aligned." Use bolding, tables, and lists for readability.
    Ensure strict Markdown. No preamble, just the content.
    """
    
    response = model.generate_content(prompt)
    return response.text

def main():
    if not GENAI_API_KEY:
        print("❌ Error: GEMINI_API_KEY not found.")
        return

    title, focus, slug = get_next_topic()
    if not title:
        print("✅ No new topics to write. All caught up!")
        return
        
    print(f"✍️ Drafting: {title}...")
    content = generate_blog_post(title, focus)
    
    filename = os.path.join(BLOGS_DIR, f"{slug}.md")
    with open(filename, 'w') as f:
        f.write(content)
        
    print(f"✨ Successfully created {filename}")
    
    # Run refresh_content to update sitemap and index
    os.system('python3 refresh_content.py')

if __name__ == "__main__":
    main()
