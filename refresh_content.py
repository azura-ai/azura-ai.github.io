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
POST_TEMPLATE = 'src/pages/post.html'
STUDY_TEMPLATE = 'src/pages/study.html'
BASE_TEMPLATE = 'templates/base.html'
CONTENT_JSON = 'content.json'
SITEMAP_XML = 'sitemap.xml'
BASE_URL = "https://azura-ai.github.io"

md = MarkdownIt(options_update={"html": True}).enable('table')

def get_shared_components(root_path=""):
    try:
        with open('src/header.html', 'r') as f: header = f.read()
        with open('src/footer.html', 'r') as f: footer = f.read()
        if root_path:
            def safe_prefix(match):
                path = match.group(1)
                if path.startswith(('http', 'https', '/', '#', 'mailto:')): return match.group(0)
                clean_path = path.lstrip('./') 
                return f'href="{root_path}{clean_path}"'
            
            header = re.sub(r'href="([^"]+)"', safe_prefix, header)
            footer = re.sub(r'href="([^"]+)"', safe_prefix, footer)
            header = header.replace('src="', f'src="{root_path}')
            footer = footer.replace('src="', f'src="{root_path}')
        return header, footer
    except: return "", ""

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
        "description": paras[0][:160] if paras else "Read more at Azura AI.",
        "image": img if os.path.exists(img) else None,
        "raw_content": content
    }

def inject_dynamic_lists(html, content_dict, filename):
    if not content_dict: return html

    if 'blogs' in content_dict:
        blog_html = ""
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
        
        if len(content_dict['blogs']) > limit:
            blog_html += '<div class="pagination-container"><button class="load-more-btn" id="load-more-blog">Load More Insights</button></div>'
        html = re.sub(r'<!-- BLOG_START -->.*?<!-- BLOG_END -->', f'<!-- BLOG_START -->{blog_html}<!-- BLOG_END -->', html, flags=re.DOTALL)

    if 'cases' in content_dict and (filename == 'index.html' or filename == 'study.html'):
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

def build_page(page_content, title, description, root_path="", body_class="main-page", schema="", extra_scripts="", canonical_url=""):
    with open(BASE_TEMPLATE, 'r') as f: base = f.read()
    header, footer = get_shared_components(root_path)
    
    html = base.replace('[[TITLE]]', title)
    html = html.replace('[[DESCRIPTION]]', description)
    html = html.replace('[[BODY_CLASS]]', body_class)
    html = html.replace('[[HEADER]]', header)
    html = html.replace('[[FOOTER]]', footer)
    html = html.replace('[[CONTENT]]', page_content)
    html = html.replace('[[ROOT]]', root_path)
    html = html.replace('[[CANONICAL]]', canonical_url or BASE_URL)
    html = html.replace('[[SCHEMA]]', schema)
    html = html.replace('[[EXTRA_SCRIPTS]]', extra_scripts)
    
    return html

def generate_static_page(item, template_path, output_dir, content_type="blog"):
    if not os.path.exists(template_path): return
    with open(template_path, 'r') as f: page_fragment = f.read()
    
    root_val = "../../"
    target_dir = os.path.join(output_dir, item['id'])
    os.makedirs(target_dir, exist_ok=True)
    
    # Process MD to HTML
    raw_md = item['raw_content']
    h1_match = re.search(r'^# .+\n', raw_md)
    baked_md = raw_md.replace(h1_match.group(0), '') if h1_match else raw_md
    content_html = md.render(baked_md)
    
    # Fill Fragment
    fragment = page_fragment.replace('<h1 id="post-title">Loading...</h1>', f'<h1 id="post-title">{item["title"]}</h1>')
    fragment = fragment.replace('<div class="loader-pulse"></div>', content_html)
    
    word_count = len(raw_md.split())
    read_time = max(1, word_count // 200)
    fragment = fragment.replace('<span id="read-time">5 min read</span>', f'<span id="read-time">{read_time} min read</span>')
    fragment = fragment.replace('<span id="read-time">3 min read</span>', f'<span id="read-time">{read_time} min read</span>')
    
    # Social Share Links
    clean_base = BASE_URL.rstrip('/')
    canonical_url = f"{clean_base}/{output_dir}/{item['id']}/"
    encoded_url = urllib.parse.quote(canonical_url)
    encoded_title = urllib.parse.quote(item['title'])
    
    # Build complete Page
    schema_data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": item["title"],
        "description": item["description"],
        "author": { "@type": "Organization", "name": "Azura AI" },
        "publisher": { "@type": "Organization", "name": "Azura AI" },
        "datePublished": datetime.now().strftime('%Y-%m-%d')
    }
    schema_html = f'<script type="application/ld+json">{json.dumps(schema_data)}</script>'
    
    html = build_page(
        page_content=fragment,
        title=item["title"],
        description=item["subtitle"].replace("*", "").replace('"', '&quot;'),
        root_path=root_val,
        body_class="sub-page",
        schema=schema_html,
        canonical_url=canonical_url
    )
    
    html = html.replace('id="share-twitter" href="#"', f'id="share-twitter" href="https://twitter.com/intent/tweet?text={encoded_title}&url={encoded_url}"')
    html = html.replace('id="share-linkedin" href="#"', f'id="share-linkedin" href="https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}"')

    with open(os.path.join(target_dir, 'index.html'), 'w') as f: f.write(html)

def generate_sitemap(data):
    today = datetime.now().strftime('%Y-%m-%d')
    core_urls = [
        (BASE_URL + "/", today, "weekly", "1.0"),
        (BASE_URL + "/blog.html", today, "weekly", "0.8"),
        (BASE_URL + "/about.html", "2026-03-20", "monthly", "0.6"),
        (BASE_URL + "/dashboard.html", today, "daily", "0.1")
    ]
    
    blog_urls = []
    for i, b in enumerate(data['blogs']):
        blog_urls.append((f"{BASE_URL}/blog/{urllib.parse.quote(b['id'])}/", today, "monthly", "0.7"))
        
    case_urls = []
    for i, c in enumerate(data['cases']):
        case_urls.append((f"{BASE_URL}/case/{urllib.parse.quote(c['id'])}/", today, "monthly", "0.6"))
        
    all_urls = core_urls + blog_urls + case_urls
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for loc, lastmod, freq, prio in all_urls:
        xml += f'    <url>\n        <loc>{loc}</loc>\n        <lastmod>{lastmod}</lastmod>\n        <changefreq>{freq}</changefreq>\n        <priority>{prio}</priority>\n    </url>\n'
    xml += '</urlset>'
    with open(SITEMAP_XML, 'w') as f: f.write(xml)

def get_calendar_data():
    cal_file = 'content_calendar.md'
    if not os.path.exists(cal_file): return []
    with open(cal_file, 'r') as f: content = f.read()
    matches = re.findall(r'\| (\d+) \| \*\*([^*]+)\*\* \| ([^|]+) \| ([^|]+) \|', content)
    blogs_dir = 'blogs'
    existing = [f.replace('.md', '') for f in os.listdir(blogs_dir) if f.endswith('.md')]
    calendar = []
    for mid, title, keyword, intent in matches:
        slug = title.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug).strip('-')
        calendar.append({
            "id": mid,
            "title": title.strip(),
            "keyword": keyword.strip(),
            "intent": intent.strip(),
            "status": "Published" if slug in existing else "Upcoming"
        })
    return calendar

if __name__ == "__main__":
    data = {"blogs": [], "cases": []}
    for d, k in [(BLOGS_MD_DIR, "blogs"), (CASES_MD_DIR, "cases")]:
        if os.path.exists(d):
            for f in sorted(os.listdir(d)):
                if f.endswith('.md'): data[k].append(extract_metadata(os.path.join(d, f)))
    
    pages = [
        ('index.html', "Azura AI | AI Document Automation & Workflow Intelligence for Europe", "Azura AI builds enterprise-grade AI document automation, intelligent OCR workflows, and autonomous agents for European businesses. Invoice processing, healthcare claims, fraud detection, and identity verification.", "main-page"),
        ('blog.html', "AI Automation Blog | Azura AI Technical Insights", "Expert technical insights on AI automation, agentic workflows, LangGraph, Pydantic AI, and intelligent document processing from Azura AI.", "sub-page"),
        ('dashboard.html', "SEO Monitoring | Azura AI Internal Dashboard", "Real-time monitoring of SEO health, content pipeline, and discovery status for Azura AI.", "sub-page"),
        ('about.html', "About Azura AI | Enterprise AI Automation Agency", "Azura AI is a European AI automation agency specializing in document intelligence, workflow automation, and autonomous agent development.", "sub-page"),
        ('facebook.html', "Connect on Facebook | Azura AI", "Follow Azura AI on Facebook for updates on enterprise AI automation.", "sub-page"),
        ('instagram.html', "Connect on Instagram | Azura AI", "Follow Azura AI on Instagram for behind-the-scenes AI engineering.", "sub-page"),
        ('linkedin.html', "Connect on LinkedIn | Azura AI", "Connect with Azura AI on LinkedIn for enterprise AI insights.", "sub-page"),
        ('threads.html', "Connect on Threads | Azura AI", "Follow Azura AI on Threads for AI automation updates.", "sub-page"),
    ]

    # Homepage JSON-LD structured data
    homepage_schema = json.dumps([
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Azura AI",
            "url": "https://azura-ai.github.io",
            "logo": "https://azura-ai.github.io/assets/images/favicon.png",
            "description": "Enterprise-grade AI document automation, workflow intelligence, and autonomous agent development for European businesses.",
            "foundingDate": "2025",
            "areaServed": ["Europe", "Middle East"],
            "knowsAbout": ["Artificial Intelligence", "Document Automation", "OCR", "Machine Learning", "Workflow Automation", "AI Agents"],
            "sameAs": [
                "https://github.com/azura-ai"
            ],
            "contactPoint": {
                "@type": "ContactPoint",
                "contactType": "sales",
                "availableLanguage": ["English"]
            },
            "hasOfferCatalog": {
                "@type": "OfferCatalog",
                "name": "AI Automation Services",
                "itemListElement": [
                    {
                        "@type": "Offer",
                        "itemOffered": {
                            "@type": "Service",
                            "name": "Digital Foundation",
                            "description": "Premium Web Development, AI Chatbot Integration, and Managed Hosting."
                        }
                    },
                    {
                        "@type": "Offer",
                        "itemOffered": {
                            "@type": "Service",
                            "name": "Automation Suite",
                            "description": "Advanced Document Workflows, Multi-Agent systems, and CRM/ERP Integration."
                        }
                    },
                    {
                        "@type": "Offer",
                        "itemOffered": {
                            "@type": "Service",
                            "name": "Fractional AI Department",
                            "description": "Long-term strategic partnership as your internal AI R&D department."
                        }
                    }
                ]
            }
        },
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Azura AI",
            "url": "https://azura-ai.github.io",
            "potentialAction": {
                "@type": "SearchAction",
                "target": "https://azura-ai.github.io/blog.html?q={search_term_string}",
                "query-input": "required name=search_term_string"
            }
        },
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": "Is our sensitive data safe with your AI?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "Absolutely. We specialize in HIPAA and GDPR compliant workflows, using layout-aware PII redaction and local/private cloud hosting to ensure your data stays within your sovereign jurisdiction."
                    }
                },
                {
                    "@type": "Question",
                    "name": "How long does a typical AI automation implementation take?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "A Foundation setup usually takes 2-4 weeks. Enterprise Automation Suites involving deep ERP integration typically take 8-12 weeks from architecture to live production."
                    }
                },
                {
                    "@type": "Question",
                    "name": "Do we need a technical team to manage this?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": "No. Our Elite and Scaling tiers include complete managed services and hosting. We act as your internal AI department, handling all monitoring and updates."
                    }
                }
            ]
        }
    ])
    homepage_schema_html = f'<script type="application/ld+json">{homepage_schema}</script>'

    for filename, title, desc, bclass in pages:
        src_path = os.path.join('src/pages', filename)
        if os.path.exists(src_path):
            with open(src_path, 'r') as f: fragment = f.read()
            
            # Inject dynamic lists
            fragment = inject_dynamic_lists(fragment, data, filename)
            
            canonical_url = f"{BASE_URL.rstrip('/')}/{filename}" if filename != 'index.html' else BASE_URL
            schema = homepage_schema_html if filename == 'index.html' else ''
            html = build_page(fragment, title, desc, body_class=bclass, canonical_url=canonical_url, schema=schema)
            with open(filename, 'w') as f: f.write(html)
    
    for b in data['blogs']: generate_static_page(b, POST_TEMPLATE, BLOGS_HTML_DIR, "blog")
    for c in data['cases']: generate_static_page(c, STUDY_TEMPLATE, CASES_HTML_DIR, "case")
    
    meta_data = {k: [{i: v for i, v in item.items() if i != 'raw_content'} for item in data[k]] for k in data}
    
    # Dashboard stats
    words = sum([len(b['raw_content'].split()) for b in data['blogs']])
    meta_data['stats'] = {
        "total_words": words,
        "avg_words": words // len(data['blogs']) if data['blogs'] else 0,
        "velocity": "1 post/week"
    }
    
    meta_data['calendar'] = get_calendar_data()
    
    # Quick health check
    meta_data['health'] = {
        "sitemap": os.path.exists(SITEMAP_XML),
        "favicon": os.path.exists('assets/images/favicon.png'),
        "og_image": os.path.exists('assets/images/og-image.png'),
        "schema": True # Homepage injection is handled in build
    }

    with open(CONTENT_JSON, 'w') as f: json.dump(meta_data, f, indent=4)
    generate_sitemap(data)
    print("✨ Unified Templating Build Complete (with SEO Dashboard data).")
