#!/usr/bin/env python3
from pathlib import Path
import html,json,os,re

project_id=os.environ['PROJECT_ID'].strip()
public_url=os.environ['PUBLIC_URL'].strip()
project_name=os.environ['PROJECT_NAME'].strip()
description=os.environ['DESCRIPTION'].strip()
index_path=Path(os.environ.get('INDEX_PATH','index.html'))
sitemap_path=Path(os.environ.get('SITEMAP_PATH','sitemap.xml'))
root_robots=Path(os.environ['ROOT_ROBOTS_PATH']) if os.environ.get('ROOT_ROBOTS_PATH') else None
root_sitemaps=[x.strip() for x in os.environ.get('ROOT_ROBOTS_SITEMAPS','').splitlines() if x.strip()]

if not index_path.is_file():
    raise SystemExit(f'index missing: {index_path}')
s=index_path.read_text(encoding='utf-8')
if f'data-sitehub-project="{project_id}"' not in s:
    raise SystemExit(f'SiteHub loader missing before SearchOps patch: {project_id}')
if not re.search(r'</head\s*>',s,re.I) or not re.search(r'</body\s*>',s,re.I):
    raise SystemExit('initial HTML must contain closing head/body')

HB='<!-- sitehub-searchops-head:begin -->'
HE='<!-- sitehub-searchops-head:end -->'
CB='<!-- sitehub-searchops-content:begin -->'
CE='<!-- sitehub-searchops-content:end -->'

schema={
  '@context':'https://schema.org',
  '@type':'WebApplication',
  'name':project_name,
  'url':public_url,
  'description':description,
  'creator':{'@type':'Organization','name':'SuaveForge','url':'https://suaveforge.com/'},
  'isPartOf':{'@type':'WebSite','name':'SuaveForge Portfolio','url':'https://suaveforge.com/'}
}
head=f'''{HB}\n<script type="application/ld+json">{json.dumps(schema,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')}</script>\n{HE}'''
level='h2' if re.search(r'<h1\b',s,re.I) else 'h1'
e=html.escape
content=f'''{CB}
<section data-sitehub-searchops="{e(project_id,quote=True)}" aria-label="서비스 정보" style="box-sizing:border-box;position:relative;z-index:1;max-width:960px;margin:32px auto;padding:20px 24px;font:14px/1.65 system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:inherit;background:transparent">
  <{level} style="font:inherit;font-size:1.25rem;font-weight:700;margin:0 0 10px">{e(project_name)}</{level}>
  <p style="margin:0 0 14px">{e(description)}</p>
  <h3 style="font:inherit;font-size:1rem;font-weight:700;margin:14px 0 6px">이 서비스는 무엇인가요?</h3>
  <p style="margin:0 0 10px">{e(description)} 실제 화면에서 핵심 기능과 사용자 흐름을 확인할 수 있습니다.</p>
  <h3 style="font:inherit;font-size:1rem;font-weight:700;margin:14px 0 6px">어떻게 사용하나요?</h3>
  <p style="margin:0 0 10px">페이지의 주요 기능을 살펴보고 화면의 시작·검색·관리·확인 기능을 사용해 서비스 또는 프로토타입의 동작과 정보를 확인하세요.</p>
  <p style="margin:14px 0 0"><strong>운영 및 지원:</strong> SuaveForge · 서비스 소개와 문의·지원 정보는 SuaveForge를 통해 확인할 수 있습니다.</p>
</section>
{CE}'''

def replace_or_insert(src,begin,end,block,closing):
    pat=re.compile(re.escape(begin)+r'[\s\S]*?'+re.escape(end),re.I)
    if pat.search(src): return pat.sub(block,src,count=1)
    return re.sub(closing,block+'\n'+re.search(closing,src,re.I).group(0),src,count=1,flags=re.I)

s=replace_or_insert(s,HB,HE,head,r'</head\s*>')
s=replace_or_insert(s,CB,CE,content,r'</body\s*>')
index_path.write_text(s,encoding='utf-8',newline='\n')

sitemap_path.parent.mkdir(parents=True,exist_ok=True)
sitemap_path.write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{e(public_url)}</loc><lastmod>2026-09-09</lastmod><changefreq>monthly</changefreq><priority>1.0</priority></url>
</urlset>
''',encoding='utf-8',newline='\n')

if root_robots:
    root_robots.parent.mkdir(parents=True,exist_ok=True)
    lines=['User-agent: *','Allow: /','']+[f'Sitemap: {u}' for u in root_sitemaps]
    root_robots.write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8',newline='\n')

out=index_path.read_text(encoding='utf-8')
assert f'data-sitehub-project="{project_id}"' in out
assert HB in out and CB in out
assert 'application/ld+json' in out
print(f'SEARCHOPS_STATIC_ADAPTER=PASS id={project_id} index={index_path} sitemap={sitemap_path}')
