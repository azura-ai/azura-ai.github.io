import os
import json
import re
import shutil
from datetime import datetime

# Path Configuration
BLOGS_MD_DIR = 'blogs'
CASES_MD_DIR = 'cases'
BLOGS_HTML_DIR = 'blog' # physical output dir: blog/slug/index.html
CASES_HTML_DIR = 'case' # physical output dir: case/id/index.html
POST_TEMPLATE = 'post.html'
STUDY_TEMPLATE = 'study.html'
CONTENT_JSON = 'content.json'
SITEMAP_XML = 'sitemap.xml'
BASE_URL = "https://nexus-intel.github.io"

# Load Shared Components for Static Injection
def get_shared_components(root_path=""):
    try:
        with open('header.html', 'r') as f:
            header = f.read()
        with open('footer.html', 'r') as f:
            footer = f.read()
        
        # Adjust paths in components
        if root_path:
            header = header.replace('href="/', f'href="{root_path}')
            header = header.replace('src="/', f'src="{root_path}')
            header = header.replace('href="index.html"', f'href="{root_path}index.html"')
            header = header.replace('href="blog.html"', f'href="{root_path}blog.html"')
            header = header.replace('href="about.html"', f'href="{root_path}about.html"')
            
            footer = footer.replace('href="/', f'href="{root_path}')
            footer = footer.replace('src="/', f'src="{root_path}')
            footer = footer.replace('href="index.html"', f'href="{root_path}index.html"')
            footer = footer.replace('href="blog.html"', f'href="{root_path}blog.html"')
            footer = footer.replace('href="about.html"', f'href="{root_path}about.html"')
            
        return header, footer
    except Exception as e:
        print(f"⚠️ Warning: Could not load shared components: {e}")
        return "", ""

def inject_components(html, header, footer):
    """Statically injects header and footer into the HTML, replacing any existing content inside those tags."""
    # Robust replacement using regex to find <header>...</header> or <header></header>
    html = re.sub(r'<header>.*?</header>', f'<header>{header}</header>', html, flags=re.DOTALL)
    html = re.sub(r'<footer>.*?</footer>', f'<footer>{footer}</footer>', html, flags=re.DOTALL)
    
    # If <header> or <footer> don't exist at all, we might want to add them after <body>
    if '<header>' not in html:
        html = html.replace('<body class="main-page">', '<body class="main-page">\n    <header>' + header + '</header>')
        html = html.replace('<body class="sub-page">', '<body class="sub-page">\n    <header>' + header + '</header>')
    
    return html

def update_root_files():
    """Updates index.html, blog.html, about.html with latest header/footer."""
    header, footer = get_shared_components()
    for filename in ['index.html', 'blog.html', 'about.html', 'privacy.html', 'post.html', 'study.html']:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                content = f.read()
            
            new_content = inject_components(content, header, footer)
            
            if new_content != content:
                with open(filename, 'w') as f:
                    f.write(new_content)
                print(f"✨ Statically updated {filename}")

def extract_metadata(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
    subtitle_match = re.search(r'^> (.+)$', content, re.MULTILINE)
    
    # Extract first paragraph for meta description (strip markdown)
    paragraphs = re.findall(r'^(?!#|>|\-|\*|```|\|)(.{50,})', content, re.MULTILINE)
    description = paragraphs[0][:160] if paragraphs else "Read more on Nexus Intelligence."
    
    title = title_match.group(1) if title_match else os.path.basename(filepath).replace('.md','').replace('-',' ').title()
    subtitle = subtitle_match.group(1) if subtitle_match else "Click to read more..."
    
    # Extract Date from content or use file mtime
    date_match = re.search(r'Date:\s*([\d-]+)', content)
    if date_match:
        date_str = date_match.group(1)
    else:
        mtime = os.path.getmtime(filepath)
        date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
    
    post_id = os.path.basename(filepath).replace('.md', '')
    
    # Determine image if exists
    image_path = f"assets/blog/{post_id}.png"
    if not os.path.exists(image_path):
        image_path = f"assets/blog/{post_id}.jpg"
    
    # Custom mapping for already named assets
    manual_mapping = {
        "gpt-5-vs-gemini-2-5-pro-vs-claude-4": "assets/blog/llm-comparison.png",
        "top-10-ai-automation-tools-for-business-in-2026": "assets/blog/ai-tools.png",
        "how-to-build-an-ai-agent-with-langgraph-step-by-step-python-tutorial": "assets/blog/langgraph-agents.png"
    }
    if post_id in manual_mapping:
        if os.path.exists(manual_mapping[post_id]):
            image_path = manual_mapping[post_id]

    return {
        "id": post_id,
        "title": title,
        "subtitle": subtitle,
        "description": description[:180],
        "date": date_str,
        "image": image_path if os.path.exists(image_path) else None,
        "raw_md": content
    }

def generate_static_page(item, template_path, output_dir, is_blog=True):
    """Generates a physical index.html for the item (Clean URL structure)."""
    with open(template_path, 'r') as f:
        html = f.read()
    
    # Replace Metadata for non-JS crawlers (SEO Peak)
    html = html.replace('<title>Blog | Nexus Intelligence</title>', f'<title>{item["title"]} | Nexus Intelligence</title>')
    html = html.replace('<title>Case Study | Nexus Intelligence</title>', f'<title>{item["title"]} | Case Study | Nexus Intelligence</title>')
    
    # Replace meta description placeholder
    html = re.sub(r'<meta name="description" content="[^"]*">', 
                  f'<meta name="description" content="{item["description"]}">', html)
    
    # Inject Canonical URL
    canonical_url = f"{BASE_URL}/{output_dir}/{item['id']}/"
    if '<link rel="canonical"' in html:
        html = re.sub(r'<link rel="canonical" href="[^"]*">', 
                      f'<link rel="canonical" href="{canonical_url}">', html)
    else:
        html = html.replace('</head>', f'    <link rel="canonical" href="{canonical_url}">\n</head>')

    # Inject ROOT_PATH for loader.js
    html = html.replace('<script src="loader.js" defer></script>', 
                       '<script>var ROOT_PATH = "../../";</script>\n    <script src="../../loader.js" defer></script>')

    # Adjust relative paths (since we are now 2 levels deep: blog/slug/index.html)
    html = html.replace('href="style.css', 'href="../../style.css')
    html = html.replace('src="script.js"', 'src="../../script.js"')
    html = html.replace('href="index.html"', 'href="../../index.html"')
    html = html.replace('href="blog.html"', 'href="../../blog.html"')
    html = html.replace('href="about.html"', 'href="../../about.html"')
    
    # Correct contact links in footer/nav within the template
    html = html.replace('href="/#contact"', 'href="../../index.html#contact"')
    html = html.replace('href="/#hero"', 'href="../../index.html#hero"')
    html = html.replace('href="/#services"', 'href="../../index.html#services"')
    html = html.replace('href="/#work"', 'href="../../index.html#work"')
    
    # Fetch paths in JS
    html = html.replace('fetch(`blogs/${blogId}.md`)', 'fetch(`../../blogs/${blogId}.md`)')
    html = html.replace('fetch(`cases/${studyId}.md`)', 'fetch(`../../cases/${studyId}.md`)')
    html = html.replace('fetch(\'content.json\')', 'fetch(\'../../content.json\')')

    # Ensure output dir exists
    target_path = os.path.join(output_dir, item['id'])
    os.makedirs(target_path, exist_ok=True)
    
    # Static Injection of Components
    header, footer = get_shared_components(root_path="../../")
    html = inject_components(html, header, footer)
    
    with open(os.path.join(target_path, 'index.html'), 'w') as f:
        f.write(html)

def refresh():
    # 0. Initial update of master templates and root files
    update_root_files()
    
    data = {"blogs": [], "cases": []}
    
    # 1. Gather Content
    if os.path.exists(BLOGS_MD_DIR):
        for f in sorted(os.listdir(BLOGS_MD_DIR)):
            if f.endswith('.md'):
                meta = extract_metadata(os.path.join(BLOGS_MD_DIR, f))
                data["blogs"].append(meta)
                generate_static_page(meta, POST_TEMPLATE, BLOGS_HTML_DIR, True)
                
    if os.path.exists(CASES_MD_DIR):
        for f in sorted(os.listdir(CASES_MD_DIR)):
            if f.endswith('.md'):
                meta = extract_metadata(os.path.join(CASES_MD_DIR, f))
                data["cases"].append(meta)
                generate_static_page(meta, STUDY_TEMPLATE, CASES_HTML_DIR, False)
                
    # 2. Save content.json (stripping raw_md to keep it small)
    json_data = {
        "blogs": [{k: v for k, v in b.items() if k != 'raw_md'} for b in data["blogs"]],
        "cases": [{k: v for k, v in c.items() if k != 'raw_md'} for c in data["cases"]]
    }
    with open(CONTENT_JSON, 'w') as f:
        json.dump(json_data, f, indent=4)
        
    print(f"✅ Refreshed content.json ({len(data['blogs'])} blogs, {len(data['cases'])} cases)")
    print(f"📂 Generated Clean URLs in /{BLOGS_HTML_DIR} and /{CASES_HTML_DIR}")
    
    # 3. Auto-generate sitemap.xml
    generate_sitemap(json_data)

def generate_sitemap(data):
    today = datetime.now().strftime('%Y-%m-%d')
    urls = [
        {"loc": f"{BASE_URL}/", "priority": "1.0", "changefreq": "weekly"},
        {"loc": f"{BASE_URL}/blog.html", "priority": "0.9", "changefreq": "weekly"},
        {"loc": f"{BASE_URL}/about.html", "priority": "0.7", "changefreq": "monthly"},
        {"loc": f"{BASE_URL}/privacy.html", "priority": "0.3", "changefreq": "yearly"},
    ]
    
    for blog in data.get("blogs", []):
        urls.append({
            "loc": f"{BASE_URL}/blog/{blog['id']}/",
            "priority": "0.8",
            "changefreq": "monthly"
        })
    
    for case in data.get("cases", []):
        urls.append({
            "loc": f"{BASE_URL}/case/{case['id']}/",
            "priority": "0.8",
            "changefreq": "monthly"
        })
    
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        xml += f'    <url>\n'
        xml += f'        <loc>{url["loc"]}</loc>\n'
        xml += f'        <lastmod>{today}</lastmod>\n'
        if "changefreq" in url:
            xml += f'        <changefreq>{url["changefreq"]}</changefreq>\n'
        xml += f'        <priority>{url["priority"]}</priority>\n'
        xml += f'    </url>\n'
    xml += '</urlset>\n'
    
    with open(SITEMAP_XML, 'w') as f:
        f.write(xml)
    print(f"✅ Auto-generated sitemap.xml ({len(urls)} URLs)")

if __name__ == "__main__":
    refresh()
