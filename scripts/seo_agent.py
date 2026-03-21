import os
import json
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# --- Models ---
class SEORecommendations(BaseModel):
    primary_keyword: str
    secondary_keywords: list[str]
    meta_title: str
    meta_description: str
    internal_links: list[str]
    improvement_suggestions: str

class DiscoveredTopic(BaseModel):
    title: str = Field(description="The catchy, SEO-optimized title for the new blog post")
    justification: str = Field(description="Why this topic was chosen based on current trends and existing gaps")
    target_audience: str = Field(description="The primary audience for this post (Developers or Business Leaders)")

# --- Agents ---

# Specialist Agent for Strategy
seo_agent = Agent(
    'google-gla:gemini-flash-latest',
    result_type=SEORecommendations,
    system_prompt=(
        "You are a Senior SEO Specialist for a high-end AI Automation Agency. "
        "Your goal is to ensure every blog post ranks #1 on Google. "
        "Use the tools to research internal links and ensure no duplication."
    ),
)

# Discovery Agent for Finding Topics
discovery_agent = Agent(
    'google-gla:gemini-flash-latest',
    result_type=DiscoveredTopic,
    system_prompt=(
        "You are an AI Content Strategist. Your job is to analyze LinkedIn trend data and "
        "existing blog posts to identify the SINGLE most high-potential topic to write about next. "
        "Choose topics that have high business ROI or solve a specific developer pain point in 2026. "
        "Avoid any topics that are already covered in the existing content."
    ),
)

# --- Tools ---

@seo_agent.tool
@discovery_agent.tool
def get_existing_content(ctx: RunContext[None]) -> str:
    """Returns a list of existing blog titles for internal linking and deduplication."""
    blogs_dir = 'blogs'
    existing = []
    if os.path.exists(blogs_dir):
        for f in os.listdir(blogs_dir):
            if f.endswith('.md'):
                title = f.replace('.md', '').replace('-', ' ').title()
                existing.append(title)
    return "\n".join(existing) if existing else "No existing content found."

@discovery_agent.tool
def read_linkedin_trends(ctx: RunContext[None]) -> str:
    """Reads the latest trending snippets found by the LinkedIn scraper."""
    leads_file = 'scripts/linkedin_leads.json'
    if os.path.exists(leads_file):
        with open(leads_file, 'r') as f:
            data = json.load(f)
            # Flatten to a readable summary of snippets
            summary = []
            for niche, posts in data.items():
                for post in posts[:3]: # Top 3 per niche
                    summary.append(f"[{niche}] {post.get('snippet', '')}")
            return "\n".join(summary)
    return "No trend data found. Scraper needs to run first."

# --- Helper Functions ---

async def get_seo_strategy(topic: str):
    """Get detailed SEO recommendations for a specific topic."""
    result = await seo_agent.run(f"Create an SEO strategy for: {topic}")
    return result.data

async def discover_next_topic():
    """Autonomously decide on the next best blog topic."""
    result = await discovery_agent.run("Analyze current trends and existing content to find the next best blog topic.")
    return result.data
