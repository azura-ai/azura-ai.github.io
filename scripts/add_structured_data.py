#!/usr/bin/env python3
"""Add JSON-LD structured data to all pages for better Google indexing.
Adds Organization, Article, and BreadcrumbList schemas."""

import json
import os
import re

CONTENT_FILE = os.path.join(os.path.dirname(__file__), '..', 'content.json')
BLOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'blog')
CASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'case')
ROOT_DIR = os.path.join(os.path.dirname(__file__), '..')
BASE_URL = 'https://nexus-intel.github.io'

def make_org_schema():
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Nexus Intelligence",
        "url": BASE_URL,
        "logo": f"{BASE_URL}/assets/images/favicon.png",
        "description": "AI automation agency specializing in document intelligence, agentic workflows, and enterprise automation for European businesses.",
        "sameAs": ["https://github.com/nexus-intel"]
    }, indent=2)

def make_article_schema(title, description, slug, section="blog", date="2026-03-20"):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title[:110],
        "description": description[:160],
        "author": {
            "@type": "Organization",
            "name": "Nexus Intelligence",
            "url": BASE_URL
        },
        "publisher": {
            "@type": "Organization",
            "name": "Nexus Intelligence",
            "logo": {
                "@type": "ImageObject",
                "url": f"{BASE_URL}/assets/images/favicon.png"
            }
        },
        "datePublished": date,
        "dateModified": date,
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"{BASE_URL}/{section}/{slug}/"
        }
    }, indent=2)

def make_breadcrumb_schema(section, title, slug):
    section_name = "Blog" if section == "blog" else "Case Studies"
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": BASE_URL
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": section_name,
                "item": f"{BASE_URL}/blog.html" if section == "blog" else BASE_URL
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": title[:60]
            }
        ]
    }, indent=2)

def inject_jsonld(html_path, schemas):
    """Inject JSON-LD script tags before </head>."""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Skip if already has structured data
    if 'application/ld+json' in content:
        return False
    
    script_tags = '\n'.join([
        f'    <script type="application/ld+json">\n{schema}\n    </script>'
        for schema in schemas
    ])
    
    content = content.replace('</head>', f'{script_tags}\n</head>')
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

def main():
    data = json.load(open(CONTENT_FILE))
    fixed = 0
    
    # Add Organization schema to homepage
    index_path = os.path.join(ROOT_DIR, 'index.html')
    if inject_jsonld(index_path, [make_org_schema()]):
        print("  ✅ index.html (Organization)")
        fixed += 1
    
    # Staggered dates for blogs
    blog_dates = {}
    start_day = 10
    for i, blog in enumerate(data.get('blogs', [])):
        day = start_day + (i % 18)
        blog_dates[blog['id']] = f"2026-03-{day:02d}"
    
    # Fix blog posts
    for blog in data.get('blogs', []):
        slug = blog['id']
        index_path = os.path.join(BLOG_DIR, slug, 'index.html')
        if os.path.exists(index_path):
            desc = blog.get('subtitle', blog.get('description', '')).replace('*', '')
            date = blog_dates.get(slug, '2026-03-20')
            schemas = [
                make_article_schema(blog['title'], desc, slug, 'blog', date),
                make_breadcrumb_schema('blog', blog['title'], slug)
            ]
            if inject_jsonld(index_path, schemas):
                print(f"  ✅ blog/{slug}")
                fixed += 1
    
    # Case study dates
    case_dates = {}
    for i, case in enumerate(data.get('cases', [])):
        day = 15 + (i % 6)
        case_dates[case['id']] = f"2026-03-{day:02d}"
    
    # Fix case studies
    for case in data.get('cases', []):
        slug = case['id']
        index_path = os.path.join(CASE_DIR, slug, 'index.html')
        if os.path.exists(index_path):
            desc = case.get('subtitle', case.get('description', '')).replace('*', '')
            date = case_dates.get(slug, '2026-03-18')
            schemas = [
                make_article_schema(case['title'], desc, slug, 'case', date),
                make_breadcrumb_schema('case', case['title'], slug)
            ]
            if inject_jsonld(index_path, schemas):
                print(f"  ✅ case/{slug}")
                fixed += 1
    
    print(f"\n🎯 Added structured data to {fixed} pages.")

if __name__ == '__main__':
    main()
