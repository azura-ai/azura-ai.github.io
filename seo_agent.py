import os
import re
import json
import google.generativeai as genai
from datetime import datetime

# Configuration
TOPICS_FILE = 'vibe_topics.md'
BLOGS_DIR = 'blogs'
GENAI_API_KEY = os.getenv('GEMINI_API_KEY')

# Company context for consistent, authoritative writing
COMPANY_CONTEXT = """
Azura AI is a European AI automation agency based in serving the EU and Middle East.
We specialize in:
- Intelligent Document Processing (invoices, receipts, insurance cards, passports)
- AI-powered chatbots for appointment booking and customer service
- Fraud detection systems for fintech
- Healthcare document automation (HIPAA/GDPR compliant)
- Identity verification (KYC) automation

Our tech stack: Python, Pydantic AI, LangGraph, FastAPI, Google Gemini API, Docker.
Website: https://azura-ai.github.io
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
    """Generate a high-quality, human-like blog post using a detailed system prompt."""
    genai.configure(api_key=GENAI_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    system_prompt = f"""You are a senior technical content writer at Azura AI, a European AI automation agency.

ABOUT THE COMPANY:
{COMPANY_CONTEXT}

WRITING RULES — FOLLOW THESE EXACTLY:

1. VOICE & TONE:
   - Write like a knowledgeable engineer explaining to a smart business colleague
   - Be confident but never salesy or hype-driven
   - NO buzzwords like "game-changer", "revolutionary", "cutting-edge", "unlock", "supercharge"
   - NO filler sentences like "In today's fast-paced world..." or "As we all know..."
   - Use specific numbers, metrics, and technical details instead of vague claims

2. STRUCTURE (follow this exactly):
   - H1: The exact title provided
   - A blockquote (>) with a compelling one-line summary (this becomes the meta description)
   - An opening paragraph (3-4 sentences) that states the specific problem and why it matters NOW
   - 3-5 H2 sections with substantive content (not fluff)
   - Include at least ONE working Python code example that demonstrates a real technique
   - Include at least ONE comparison table with real data or realistic estimates
   - A practical "Implementation Checklist" or "Getting Started" section near the end
   - A brief closing paragraph (2-3 sentences) with a single, natural mention of Azura AI

3. SEO REQUIREMENTS:
   - Use the target keyword naturally in the H1, first paragraph, one H2, and conclusion
   - Use related long-tail variations throughout (don't repeat the exact keyword unnaturally)
   - Internal links: reference 1-2 other relevant pages using relative Markdown links
   - Word count: 1500-2500 words (long enough to be thorough, not padded)

4. WHAT MAKES THIS DIFFERENT FROM AI SPAM:
   - Include specific version numbers, library names, and real API references
   - Reference actual industry standards (HIPAA, GDPR, PCI-DSS) where relevant
   - Include realistic cost estimates or time savings based on industry benchmarks
   - Acknowledge limitations and edge cases (real experts do this)
   - Use concrete examples: "A 500-bed hospital processing 2,000 claims/day" not "organizations"

5. ABSOLUTELY DO NOT:
   - Start with "In today's..." or "In the ever-evolving..."
   - Use the word "delve" or "leverage" or "utilize"
   - Include a generic "What is X?" section that reads like a Wikipedia intro
   - End every section with a rhetorical question
   - Use emojis in the body text
   - Include placeholder links to pages that don't exist
"""

    user_prompt = f"""Write a blog post for the Azura AI website.

Title: {title}
Target Keyword: {keyword}
Reader Intent: {intent}

Remember: Write this as if YOU personally built the system being described. 
Reference specific Python libraries, API endpoints, and architecture decisions.
The reader should finish this post feeling like they learned something concrete they can act on.

Output ONLY the Markdown content. No preamble, no "here's the blog post", just the content starting with # {title}"""

    response = model.generate_content(
        [system_prompt, user_prompt],
        generation_config=genai.GenerationConfig(
            temperature=0.7,  # Some creativity but not hallucination-prone
            max_output_tokens=4096
        )
    )
    return response.text

def validate_content(content, title):
    """Basic quality checks before saving."""
    issues = []
    
    word_count = len(content.split())
    if word_count < 800:
        issues.append(f"Too short: {word_count} words (minimum 800)")
    
    if not content.startswith(f'# {title}') and not content.startswith(f'# '):
        issues.append("Missing H1 title")
    
    if '```python' not in content and '```py' not in content:
        issues.append("Missing Python code example")
    
    if '|' not in content:
        issues.append("Missing comparison table")
    
    # Check for spam signals
    spam_phrases = [
        "in today's fast-paced",
        "game-changer", "game changer",
        "revolutionize", "revolutionary",
        "in the ever-evolving",
        "as we all know",
        "without further ado",
        "it's no secret that"
    ]
    for phrase in spam_phrases:
        if phrase.lower() in content.lower():
            issues.append(f"Spam phrase detected: '{phrase}'")
    
    return issues

def main():
    if not GENAI_API_KEY:
        print("❌ Error: GEMINI_API_KEY not found in environment.")
        return

    title, keyword, intent, slug = get_next_topic()
    if not title:
        print("✅ All topics have been written. Update vibe_topics.md with new topics.")
        return
        
    print(f"✍️  Drafting: {title}")
    print(f"   Keyword: {keyword}")
    print(f"   Intent:  {intent}")
    print(f"   Slug:    {slug}")
    
    content = generate_blog_post(title, keyword, intent)
    
    # Run quality validation
    issues = validate_content(content, title)
    if issues:
        print(f"\n⚠️  Quality issues detected:")
        for issue in issues:
            print(f"   - {issue}")
        
        # If there are spam phrases, try regenerating once
        spam_issues = [i for i in issues if 'Spam phrase' in i]
        if spam_issues:
            print("\n🔄 Regenerating to fix spam phrases...")
            content = generate_blog_post(title, keyword, intent)
            issues = validate_content(content, title)
            if issues:
                print(f"   Still has issues (proceeding anyway):")
                for issue in issues:
                    print(f"   - {issue}")
    
    # Save the content
    filename = os.path.join(BLOGS_DIR, f"{slug}.md")
    with open(filename, 'w') as f:
        f.write(content)
        
    word_count = len(content.split())
    print(f"\n✨ Created {filename} ({word_count} words)")
    
    # Rebuild the site
    print("🔨 Rebuilding site...")
    os.system('python3 refresh_content.py')
    print("✅ Done.")

if __name__ == "__main__":
    main()
