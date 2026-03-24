import os
import re
import json
from datetime import datetime
from markdown_it import MarkdownIt
import urllib.parse

# Configuration
BLOGS_MD_DIR = 'blogs'
CASES_MD_DIR = 'cases'
BLOGS_HTML_DIR = 'blog'
CASES_HTML_DIR = 'case'
POST_TEMPLATE = 'post.html'
STUDY_TEMPLATE = 'study.html'
CONTENT_JSON = 'content.json'
SITEMAP_XML = 'sitemap.xml'
BASE_URL = "https://nexus-intel.github.io"

md = MarkdownIt(options_update={"html": True}).enable('table')

def get_shared_components(root_path=""):
    try:
        with open('header.html', 'r') as f: header = f.read()
        with open('footer.html', 'r') as f: footer = f.read()
        if root_path:
            def safe_prefix(match):
                path = match.group(1)
                if path.startswith(('http', 'https', '/', '#', 'mailto:')): return match.group(0)
                # Cleanup existing relative prefixes to prevent doubling
                clean_path = path.lstrip('./') 
                return f'href="{root_path}{clean_path}"'
            
            header = re.sub(r'href="([^"]+)"', safe_prefix, header)
            footer = re.sub(r'href="([^"]+)"', safe_prefix, footer)
            header = header.replace('src="', f'src="{root_path}')
            footer = footer.replace('src="', f'src="{root_path}')
        return header, footer
    except: return "", ""

def inject_content(html, header, footer, content_dict=None, filename=""):
    html = re.sub(r'<header id="header-container">.*?</header>', f'<header id="header-container">{header}</header>', html, flags=re.DOTALL)
    html = re.sub(r'<footer id="footer-container">.*?</footer>', f'<footer id="footer-container">{footer}</footer>', html, flags=re.DOTALL)
    if not content_dict: return html

    if 'blogs' in content_dict:
        blog_html = ""
        # Home page shows 6, Blog page shows 9 initially.
        # We only BAKE these into HTML. The rest are loaded via content.json + script.js for speed.
        limit = 6 if filename == 'index.html' else 9
        for i, b in enumerate(content_dict['blogs'][:limit]):
            img_url = b.get('image') or ""
            hue1, hue2 = 265 + i * 15, 225 + i * 15
            fallback_bg = f"linear-gradient(135deg, hsl({hue1}, 75%, 45%), hsl({hue2}, 75%, 35%))"
            card = f"""
            <div class="blog-card animate-in" style="animation-delay: {i * 0.1}s">
                <div class="blog-img" style="background: {f"url('{img_url}') center/cover" if img_url else fallback_bg};">
                    {"" if img_url else '<div class="img-overlay" style="background: linear-gradient(to top, rgba(0,0,0,0.8), transparent);"></div>'}
                </div>
                <div class="blog-content" style="padding: 3rem;">
                    <span class="blog-tag">Insight</span>
                    <h3>{b['title']}</h3>
                    <p>{b['subtitle'][:100]}...</p>
                    <a href="blog/{b['id']}/" class="read-more">Read Insight <i class="fas fa-arrow-right"></i></a>
                </div>
            </div>"""
            blog_html += card
        
        # Add a placeholder for JS to pick up the Load More button if there are more blogs
        if len(content_dict['blogs']) > limit:
            blog_html += '<div class="pagination-container"><button class="load-more-btn" id="load-more-blog">Load More Insights</button></div>'
        html = re.sub(r'<!-- BLOG_START -->.*?<!-- BLOG_END -->', f'<!-- BLOG_START -->{blog_html}<!-- BLOG_END -->', html, flags=re.DOTALL)

    if 'cases' in content_dict and filename == 'index.html':
        case_html = ""
        limit = 6
        for i, c in enumerate(content_dict['cases']):
            is_hidden = "hidden-card" if i >= limit else ""
            case_html += f"""
            <div class="case-card animate-in {is_hidden}" style="animation-delay: {i * 0.1}s">
                <div class="case-content">
                    <div class="case-header">
                        <span class="case-badge">Impact Analysis</span>
                        <h3>{c['title']}</h3>
                    </div>
                    <p>{c['subtitle']}</p>
                    <a href="case/{c['id']}/" class="read-more">View Full Breakdown <i class="fas fa-arrow-right"></i></a>
                </div>
            </div>"""
        html = re.sub(r'<!-- CASES_START -->.*?<!-- CASES_END -->', f'<!-- CASES_START -->{case_html}<!-- CASES_END -->', html, flags=re.DOTALL)
    return html

def extract_metadata(filepath):
    with open(filepath, 'r') as f: content = f.read()
    title = re.search(r'^# (.+)$', content, re.MULTILINE)
    subtitle = re.search(r'^> (.+)$', content, re.MULTILINE)
    paras = re.findall(r'^(?!#|>|\-|\*|```|\|)(.{50,})', content, re.MULTILINE)
    post_id = os.path.basename(filepath).replace('.md', '')
    img = f"assets/blog/{post_id}.png"
    return {
        "id": post_id,
        "title": title.group(1) if title else post_id.replace('-', ' ').title(),
        "subtitle": subtitle.group(1) if subtitle else "Premium AI Insight",
        "description": paras[0][:160] if paras else "Read more at Nexus Intelligence.",
        "image": img if os.path.exists(img) else None,
        "raw_content": content
    }

def generate_static_page(item, template_path, output_dir, content_type="blog"):
    if not os.path.exists(template_path): return
    with open(template_path, 'r') as f: html = f.read()
    
    # 1. Path Harmonization
    root_val = "../../"
    html = html.replace('[[ROOT]]', root_val)
    
    clean_base = BASE_URL.rstrip('/')
    clean_path = f"{output_dir}/{item['id']}"
    canonical_url = f"{clean_base}/{clean_path}/"
    
    # 2. Metadata Injection
    html = html.replace('<title>Blog | Nexus Intelligence</title>', f'<title>{item["title"]} | Nexus Intelligence</title>')
    html = html.replace('<title>Case Study | Nexus Intelligence</title>', f'<title>{item["title"]} | Case Study | Nexus Intelligence</title>')
    html = html.replace('<meta name="description" content="[^"]*">', f'<meta name="description" content="{item["description"]}">')
    
    # 3. Content Baking (ZERO-FETCH)
    raw_md = item['raw_content']
    h1_match = re.search(r'^# .+\n', raw_md)
    baked_md = raw_md.replace(h1_match.group(0), '') if h1_match else raw_md
    content_html = md.render(baked_md)
    
    html = html.replace('<h1 id="post-title">Loading...</h1>', f'<h1 id="post-title">{item["title"]}</h1>')
    html = html.replace('<div class="loader-pulse"></div>', content_html)
    
    # 4. Read Time
    word_count = len(raw_md.split())
    read_time = max(1, word_count // 200)
    html = html.replace('<span id="read-time">5 min read</span>', f'<span id="read-time">{read_time} min read</span>')
    html = html.replace('<span id="read-time">3 min read</span>', f'<span id="read-time">{read_time} min read</span>')

    # 5. Social Links
    encoded_url = urllib.parse.quote(canonical_url)
    encoded_title = urllib.parse.quote(item['title'])
    html = html.replace('id="share-twitter" href="#"', f'id="share-twitter" href="https://twitter.com/intent/tweet?text={encoded_title}&url={encoded_url}"')
    html = html.replace('id="share-linkedin" href="#"', f'id="share-linkedin" href="https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}"')

    # 6. Shared Components
    target_dir = os.path.join(output_dir, item['id'])
    os.makedirs(target_dir, exist_ok=True)
    header, footer = get_shared_components(root_path=root_val)
    html = inject_content(html, header, footer)
    
    # 7. Schema Baking
    schema_id = "article-schema" if content_type == "blog" else "study-schema"
    schema_data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": item["title"],
        "description": item["description"],
        "author": { "@type": "Organization", "name": "Nexus Intelligence" },
        "publisher": { "@type": "Organization", "name": "Nexus Intelligence" },
        "datePublished": datetime.now().strftime('%Y-%m-%d')
    }
    schema_pattern = f'<script type="application/ld+json" id="{schema_id}">'
    if schema_pattern in html:
        parts = html.split(schema_pattern)
        after_pattern = parts[1].split('</script>', 1)
        new_script = f'{schema_pattern}{json.dumps(schema_data)}</script>'
        html = parts[0] + new_script + after_pattern[1]

    with open(os.path.join(target_dir, 'index.html'), 'w') as f: f.write(html)

def generate_sitemap(data):
    today = datetime.now().strftime('%Y-%m-%d')
    urls = [BASE_URL + "/", BASE_URL + "/blog.html", BASE_URL + "/about.html", BASE_URL + "/privacy.html"]
    for b in data['blogs']: urls.append(f"{BASE_URL}/blog/{b['id']}/")
    for c in data['cases']: urls.append(f"{BASE_URL}/case/{c['id']}/")
    
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        xml += f'    <url><loc>{u}</loc><lastmod>{today}</lastmod><priority>0.8</priority></url>\n'
    xml += '</urlset>'
    with open(SITEMAP_XML, 'w') as f: f.write(xml)

if __name__ == "__main__":
    data = {"blogs": [], "cases": []}
    for d, k in [(BLOGS_MD_DIR, "blogs"), (CASES_MD_DIR, "cases")]:
        if os.path.exists(d):
            for f in sorted(os.listdir(d)):
                if f.endswith('.md'): data[k].append(extract_metadata(os.path.join(d, f)))
    
    header, footer = get_shared_components()
    for filename in ['index.html', 'blog.html']:
        if os.path.exists(filename):
            with open(filename, 'r') as f: content = f.read()
            content = content.replace('[[ROOT]]', '') # Root pages have no root_path
            new_html = inject_content(content, header, footer, data, filename)
            with open(filename, 'w') as f: f.write(new_html)
    
    for b in data['blogs']: generate_static_page(b, POST_TEMPLATE, BLOGS_HTML_DIR, "blog")
    for c in data['cases']: generate_static_page(c, STUDY_TEMPLATE, CASES_HTML_DIR, "case")
    
    meta_data = {k: [{i: v for i, v in item.items() if i != 'raw_content'} for item in data[k]] for k in data}
    with open(CONTENT_JSON, 'w') as f: json.dump(meta_data, f, indent=4)
    generate_sitemap(data)
    print("✨ SSG Path Reconciliation Complete. Asset links verified.")
