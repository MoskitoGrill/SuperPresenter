# Frozen from commit 0965cf4 for compatibility tests only.
def readInstructions(self):
    txt = self.repetitions
    legals = self.legalSections()
    insts = []
    b = ''
    used = []
    err = [0]
    idx = 0
    conn = [0]
    while idx < len(txt):
        a = txt[idx]
        if a == '(':
            insts = ['*'] + insts
            conn.append(0)
            idx += 1
        elif a == ')':
            idx += 1
            a = txt[idx] if idx < len(txt) else ''
            if a == '*':
                idx += 1
                while idx < len(txt):
                    a = txt[idx]
                    if ord(a) >= 48 and ord(a) <= 57:
                        b += a
                    else:
                        break
                    idx += 1
                if b == '':
                    err = [2, idx]
                    break
                n = int(b)
                b = ''
            else:
                n = 2
            for idx2 in range(len(insts)):
                b = 'err'
                if insts[idx2] == '*':
                    insts = insts[0:idx2] + [conn[-1],'conn',n,'mult'] \
                        + insts[idx2+1:]
                    conn.pop(-1)
                    conn[-1] += 1
                    b = ''
                    break
            if b == 'err':
                err = [1]
                break
        elif a == ' ':
            idx += 1
        else:
            conn[-1] += 1
            while a != ' ' and a != '.' and a != '(' and a != ')':
                b += a
                idx += 1
                if idx >= len(txt):
                    break
                a = txt[idx]
            if b in legals:
                if b in used:
                    k = used.index(b)
                else:
                    k = len(used)
                    used.append(b)
            else:
                err = [3, b]
                break
            b = ''
            if a == ' ' or a == ')' or a == '(':
                insts = [k,'all'] + insts
            elif a == '.':
                idx += 1
                if idx > len(txt):
                    err = [4, idx]
                    break
                while idx < len(txt):
                    a = txt[idx]
                    if ord(a) >= 48 and ord(a) <= 57:
                        b += a
                        idx += 1
                    else:
                        break
                if b == '':
                    err = [4, idx]
                    break
                n0 = int(b)
                if idx >= len(txt):
                    insts = [k,n0,'line'] + insts
                    break
                b = ''
                a = txt[idx]
                if a == ':':
                    idx += 1
                    if idx > len(txt):
                        err = [5, idx]
                        break
                    while idx < len(txt):
                        a = txt[idx]
                        if ord(a) >= 48 and ord(a) <= 57:
                            b += a
                            idx += 1
                        else:
                            break
                    if b == '':
                        err = [5, idx]
                        break
                    n = int(b)
                    if n <= n0:
                        err = [6, idx]
                        break
                    insts= [k,n0,n,'lins'] + insts
                    b = ''

                else:
                    insts = [k,n0,'line'] + insts
            elif idx >= len(txt):
                insts = [k,'all'] + insts
    if err[0] > 0:
        return err
    if len(conn) > 1:
        err = [1]
        return err
    for inst in insts:
        if inst == '*':
            err = [1]
            return err
    insts = insts + [conn[0],'conn']
    self.instructions = insts
    self.usedSections = used
    return err
