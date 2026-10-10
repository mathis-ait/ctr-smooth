"""Offsets des champs de State d'apres runtime/state.h (tous des mots de 32 bits).
  stateoff.py [champ]   ou import : off('vstick')"""
import os, re, sys
H = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'runtime', 'state.h')
def table():
    src = open(H, encoding='utf-8').read()
    body = src[src.index('typedef struct {') + len('typedef struct {'):src.index('} State;')]
    body = re.sub(r'/\*.*?\*/', '', body, flags=re.S)
    offs, o = {}, 0
    for decl in body.split(';'):
        decl = decl.strip()
        if not decl or decl.startswith('typedef'):
            continue
        for name in decl.split(None, 1)[1].split(','):
            name = name.strip().lstrip('*')
            m = re.match(r'(\w+)(?:\[(\d+)\])?', name)
            n = int(m.group(2) or 1)
            offs[m.group(1)] = o
            o += 4 * n
    return offs
def off(name):
    return table()[name]
if __name__ == '__main__':
    t = table()
    for k in (sys.argv[1:] or t):
        print('%-10s 0x%03x' % (k, t[k]))
