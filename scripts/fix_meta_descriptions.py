#!/usr/bin/env python3
"""Fix duplicate meta descriptions across all blog and case study pages.
Uses the subtitle from content.json as a unique, SEO-relevant meta description."""

import json
import os
import re

CONTENT_FILE = os.path.join(os.path.dirname(__file__), '..', 'content.json')
BLOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'blog')
CASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'case')

GENERIC_BLOG_META = 'Expert insights on AI automation, agentic workflows, OCR, and enterprise intelligence from Nexus Intelligence.'
GENERIC_CASE_META = 'Explore how Nexus Intelligence delivers measurable business impact through AI automation, agentic workflows, and intelligent document processing.'

def load_content():
    with open(CONTENT_FILE, 'r') as f:
        return json.load(f)

def fix_meta(html_path, new_description):
    """Replace the meta description in an HTML file."""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Escape for HTML attribute
    safe_desc = new_description.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
    # Truncate to 160 chars for SEO best practice
    if len(safe_desc) > 160:
        safe_desc = safe_desc[:157] + '...'
    
    # Replace the generic meta description
    pattern = r'<meta name="description" content="[^"]*">'
    replacement = f'<meta name="description" content="{safe_desc}">'
    
    new_content = re.sub(pattern, replacement, content, count=1)
    
    if new_content != content:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    data = load_content()
    fixed = 0
    
    # Fix blog posts
    for blog in data.get('blogs', []):
        slug = blog['id']
        index_path = os.path.join(BLOG_DIR, slug, 'index.html')
        if os.path.exists(index_path):
            # Use subtitle as meta description (more specific than generic)
            desc = blog.get('subtitle', blog.get('description', ''))
            # Clean markdown formatting
            desc = desc.replace('*', '').replace('**', '')
            if fix_meta(index_path, desc):
                print(f"  ✅ blog/{slug}")
                fixed += 1
            else:
                print(f"  ⏭️  blog/{slug} (no change needed)")
        else:
            print(f"  ⚠️  blog/{slug} (index.html not found)")
    
    # Fix case studies
    for case in data.get('cases', []):
        slug = case['id']
        index_path = os.path.join(CASE_DIR, slug, 'index.html')
        if os.path.exists(index_path):
            desc = case.get('subtitle', case.get('description', ''))
            desc = desc.replace('*', '').replace('**', '')
            if fix_meta(index_path, desc):
                print(f"  ✅ case/{slug}")
                fixed += 1
            else:
                print(f"  ⏭️  case/{slug} (no change needed)")
        else:
            print(f"  ⚠️  case/{slug} (index.html not found)")
    
    print(f"\n🎯 Fixed {fixed} pages with unique meta descriptions.")

if __name__ == '__main__':
    main()
