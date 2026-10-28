import httpx
import re

nodes = [
    'nodes/0.BtW1TBFK.js',
    'nodes/1.Z711g0cW.js',
    'nodes/2.DeBfS3Sk.js',
    'nodes/3.ChF_GTmT.js',
    'nodes/4.C5ra3I1_.js',
    'nodes/5.H_pU0PSd.js',
    'nodes/6.-ftwtBCU.js',
    'nodes/7.BIfEHfl6.js',
    'nodes/8.CzNkaeeZ.js',
    'nodes/9.COiC4YtW.js',
    'nodes/10.C313J7Z1.js',
]

client = httpx.Client(base_url='https://portal.privatemode.ai/_app/immutable/')
for n in sorted(set(nodes)):
    r = client.get(n)
    urls = set(re.findall(r'https?://[^\s"\'<>]+', r.text))
    api_routes = set(re.findall(r'/api/[^\s"\'<>]+', r.text))
    endpoints = set(re.findall(r'/v[0-9]/[^\s"\'<>]+', r.text))
    print(f'=== {n} ===')
    if urls:
        print('URLs:', [u for u in urls if not u.endswith('.js') and not u.endswith('.css')])
    if api_routes:
        print('API routes:', list(api_routes)[:10])
    if endpoints:
        print('v* routes:', list(endpoints)[:10])
