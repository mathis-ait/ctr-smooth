"""Modifie une cle d'un qt-config.ini d'Azahar (bac a sable, Azahar ferme) :
  ini_set.py <qt-config.ini> cle valeur [cle valeur ...]
Ecrit aussi « cle\\default=false » pour qu'Azahar prenne la valeur en compte."""
import re
import sys

BS = '\\'


def main():
    path = sys.argv[1]
    s = open(path, 'rb').read().decode('utf-8')
    args = sys.argv[2:]
    for key, value in zip(args[::2], args[1::2]):
        pat = re.escape(key + BS + 'default=') + r'\w+(\r?\n)' + re.escape(key + '=') + r'[^\r\n]*'
        s, n = re.subn(pat, lambda m: key + BS + 'default=false' + m.group(1) + key + '=' + value, s)
        print('%s=%s (%d)' % (key, value, n))
    open(path, 'wb').write(s.encode('utf-8'))


if __name__ == '__main__':
    main()
