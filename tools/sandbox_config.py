"""Prepare la config d'un Azahar portable (bac a sable) pour l'automatisation :
manette virtuelle Xbox 360 (vpad.py), stub GDB actif, pas de verification de MAJ.

Usage : sandbox_config.py <user/config/qt-config.ini> <guid_source> <guid_vpad>
"""
import re
import sys

BS = '\\'


def main():
    path, guid_src, guid_vpad = sys.argv[1:4]
    s = open(path, 'rb').read().decode('utf-8')
    s = s.replace(guid_src, guid_vpad)
    # Disposition Xbox : bouton 3DS A <- SDL A (0), B <- 1, X <- 2, Y <- 3
    for key, new in (('button_a', 0), ('button_b', 1), ('button_x', 2), ('button_y', 3)):
        pre = 'profiles' + BS + '1' + BS + key + '="'
        s = re.sub(re.escape(pre) + r'([^"\r\n]*?)button:\d+,',
                   lambda m, pre=pre, new=new: pre + m.group(1) + 'button:%d,' % new, s)
    for key, value in (('use_gdbstub', 'true'), ('check_for_update_on_start', 'false')):
        s = re.sub(re.escape(key + BS + 'default=') + r'\w+(\r?\n)' + re.escape(key + '=') + r'\w+',
                   lambda m, key=key, value=value: key + BS + 'default=false' + m.group(1) + key + '=' + value, s)
    open(path, 'wb').write(s.encode('utf-8'))
    for k in ('button_a=', 'button_b=', 'use_gdbstub', 'check_for_update_on_start'):
        print([line[:100] for line in s.splitlines() if k in line][:2])


if __name__ == '__main__':
    main()
