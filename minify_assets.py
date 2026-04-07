import re
import os

def minify_css(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Remove whitespace
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\s*([\{\}\:\;\,])\s*', r'\1', content)
    content = content.strip()

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Minified {input_path} to {output_path}")
    print(f"Original size: {os.path.getsize(input_path)} bytes")
    print(f"Minified size: {os.path.getsize(output_path)} bytes")

if __name__ == "__main__":
    minify_css('style.css', 'style.min.css')
