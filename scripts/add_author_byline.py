#!/usr/bin/env python3
"""Add author byline to blog and case study post-meta sections.
Injects 'By Nexus Intelligence Team' into the post header for E-E-A-T signals."""

import os
import re

BLOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'blog')
CASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'case')

AUTHOR_HTML = '<span class="meta-separator">•</span>\n                    <span class="post-author"><i class="fas fa-user-pen"></i> Nexus Intelligence Team</span>'

def inject_author(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Skip if already has author
    if 'post-author' in content:
        return False
    
    # Find the read-time span and add author after it
    # Pattern: <span id="read-time">X min read</span>
    pattern = r'(<span id="read-time">[^<]*</span>)'
    replacement = r'\1\n                    ' + AUTHOR_HTML
    
    new_content = re.sub(pattern, replacement, content, count=1)
    
    if new_content != content:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    fixed = 0
    
    for directory in [BLOG_DIR, CASE_DIR]:
        section = os.path.basename(directory)
        if not os.path.exists(directory):
            continue
        for slug in sorted(os.listdir(directory)):
            index_path = os.path.join(directory, slug, 'index.html')
            if os.path.exists(index_path):
                if inject_author(index_path):
                    print(f"  ✅ {section}/{slug}")
                    fixed += 1
                else:
                    print(f"  ⏭️  {section}/{slug} (already has author or no match)")
    
    print(f"\n🎯 Added author byline to {fixed} pages.")

if __name__ == '__main__':
    main()
