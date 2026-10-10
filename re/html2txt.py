import sys, re, html
s = open(sys.argv[1], encoding='utf-8', errors='replace').read()
# Ne garder que les messages (articles) du fil
posts = re.findall(r'<article class="message-body[^"]*".*?</article>', s, flags=re.S) or re.findall(r'<div class="bbWrapper">.*?</div>\s*</div>', s, flags=re.S)
if not posts: posts=[s]
out=[]
for p in posts:
    p = re.sub(r'<br\s*/?>', '\n', p); p = re.sub(r'</(p|div|li|pre|h\d|tr)>', '\n', p)
    p = re.sub(r'<[^>]+>', '', p); p = html.unescape(p)
    p = re.sub(r'\n{3,}', '\n\n', p)
    out.append(p.strip())
print(('\n\n' + '='*60 + '\n\n').join(out))
