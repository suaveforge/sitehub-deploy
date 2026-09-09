from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

project_id = os.environ["PROJECT_ID"].strip()
public_url = os.environ["PUBLIC_URL"].strip()
project_name = os.environ["PROJECT_NAME"].strip()
description = os.environ["DESCRIPTION"].strip()
index_path = Path(os.environ.get("INDEX_PATH", "index.html"))
sitemap_path = Path(os.environ.get("SITEMAP_PATH", str(index_path.with_name("sitemap.xml"))))
robots_path = Path(os.environ.get("ROBOTS_PATH", str(index_path.with_name("robots.txt"))))

if not re.fullmatch(r"p\d{2,}", project_id):
    raise SystemExit("invalid PROJECT_ID")
parts = urlsplit(public_url)
if parts.scheme != "https" or not parts.netloc:
    raise SystemExit("PUBLIC_URL must be absolute https URL")
if not public_url.endswith("/"):
    public_url += "/"
if not index_path.is_file():
    raise SystemExit(f"missing served index: {index_path}")

s = index_path.read_text(encoding="utf-8")
if not re.search(r"<head\b", s, re.I) or not re.search(r"</head\s*>", s, re.I):
    raise SystemExit("served index has no head")
if not re.search(r"</body\s*>", s, re.I):
    raise SystemExit("served index has no body")

def esc(value: str) -> str:
    return html.escape(value, quote=True)

def has(pattern: str) -> bool:
    return bool(re.search(pattern, s, re.I | re.S))

m = re.search(r"<title\b[^>]*>([\s\S]*?)</title\s*>", s, re.I)
title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else project_name

head_additions: list[str] = []
if not has(r'<meta\b[^>]*(?:name\s*=\s*["\']description["\']|property\s*=\s*["\']description["\'])'):
    head_additions.append(f'<meta name="description" content="{esc(description)}">')
if not has(r'<link\b[^>]*rel\s*=\s*["\'][^"\']*canonical'):
    head_additions.append(f'<link rel="canonical" href="{esc(public_url)}">')
for prop, value in [
    ("og:title", title),
    ("og:description", description),
    ("og:image", "https://sitehub.suaveforge.com/assets/namecard-default.png"),
    ("og:url", public_url),
    ("og:site_name", project_name),
]:
    if not has(r'<meta\b[^>]*property\s*=\s*["\']' + re.escape(prop) + r'["\']'):
        head_additions.append(f'<meta property="{prop}" content="{esc(value)}">')
if not has(r'<meta\b[^>]*name\s*=\s*["\']twitter:card["\']'):
    head_additions.append('<meta name="twitter:card" content="summary_large_image">')
if f'data-sitehub-project="{project_id}"' not in s and f"data-sitehub-project='{project_id}'" not in s:
    head_additions.append(f'<script async src="https://sitehub.suaveforge.com/analytics-loader.js" data-sitehub-project="{project_id}"></script>')

hb = "<!-- sitehub-searchops-complete-head:begin -->"
he = "<!-- sitehub-searchops-complete-head:end -->"
schema = {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "name": project_name,
    "url": public_url,
    "description": description,
    "creator": {"@type": "Organization", "name": "SuaveForge", "url": "https://suaveforge.com/"},
    "isPartOf": {"@type": "WebSite", "name": "SuaveForge", "url": "https://suaveforge.com/"},
}
head_block = hb + "\n" + "\n".join(head_additions) + ("\n" if head_additions else "") + '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c") + "</script>\n" + he
head_re = re.compile(re.escape(hb) + r"[\s\S]*?" + re.escape(he), re.I)
if head_re.search(s):
    s = head_re.sub(head_block, s, count=1)
else:
    s = re.sub(r"</head\s*>", head_block + "\n</head>", s, count=1, flags=re.I)

cb = "<!-- sitehub-searchops-complete-content:begin -->"
ce = "<!-- sitehub-searchops-complete-content:end -->"
heading = "h2" if has(r"<h1\b") else "h1"
content = f'''{cb}
<section data-sitehub-searchops="{esc(project_id)}" aria-label="서비스 정보" style="box-sizing:border-box;position:relative;z-index:1;max-width:1040px;margin:32px auto;padding:20px 24px;font:14px/1.65 system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:inherit;background:transparent">
  <{heading} style="font:inherit;font-size:1.25rem;font-weight:700;margin:0 0 10px">{esc(project_name)}</{heading}>
  <p style="margin:0 0 12px">{esc(description)}</p>
  <h3 style="font:inherit;font-size:1rem;font-weight:700;margin:12px 0 6px">이 서비스는 무엇을 하나요?</h3>
  <p style="margin:0 0 10px">{esc(description)} 실제 화면에서 주요 기능과 정보 흐름을 확인할 수 있습니다.</p>
  <h3 style="font:inherit;font-size:1rem;font-weight:700;margin:12px 0 6px">어떻게 사용하나요?</h3>
  <p style="margin:0 0 10px">페이지의 시작·조회·관리·확인 기능을 이용해 서비스의 핵심 흐름을 확인하세요.</p>
  <p style="margin:12px 0 0"><strong>운영 및 지원:</strong> SuaveForge · 서비스 관련 정보와 지원은 SuaveForge를 통해 확인할 수 있습니다.</p>
</section>
{ce}'''
content_re = re.compile(re.escape(cb) + r"[\s\S]*?" + re.escape(ce), re.I)
if content_re.search(s):
    s = content_re.sub(content, s, count=1)
else:
    s = re.sub(r"</body\s*>", content + "\n</body>", s, count=1, flags=re.I)

index_path.write_text(s, encoding="utf-8")
sitemap_path.parent.mkdir(parents=True, exist_ok=True)
sitemap_path.write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    f'  <url><loc>{html.escape(public_url)}</loc><lastmod>2026-09-09</lastmod><changefreq>weekly</changefreq><priority>1.0</priority></url>\n'
    '</urlset>\n',
    encoding="utf-8",
)
robots_path.parent.mkdir(parents=True, exist_ok=True)
robots_path.write_text(
    f"User-agent: *\nAllow: /\n\nSitemap: {public_url}sitemap.xml\n",
    encoding="utf-8",
)
print(f"SITEHUB_STATIC_COMPLETE=PASS project={project_id} index={index_path} sitemap={sitemap_path} robots={robots_path}")
