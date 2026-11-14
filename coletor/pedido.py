import re
def limpa(t):
    return re.sub(r'\s+', ' ', t or '').strip()
CHAVES = [r'solicitando[,:]?\s', r'requerendo[,:]?\s', r'sugerindo[,:]?\s', r'\bINDICA[R]?\b,?', r'\bREQUER(?:ER)?\b,?',
          r'apresenta[r]?\s', r'\bMOÇÃO\b']
def pedido(texto, limite=320):
    t = limpa(texto)
    m = re.search(r'Senhor Presidente,?', t, re.I)
    corpo = t[m.end():] if m else t
    melhor = None
    for c in CHAVES[:3]:
        mm = re.search(c, corpo, re.I)
        if mm and (melhor is None or mm.start() < melhor.start()): melhor = mm
    if melhor:
        trecho = corpo[melhor.end():]
    else:
        mm = re.search('|'.join(CHAVES[3:]), corpo)
        trecho = corpo[mm.end():] if mm else corpo
    trecho = re.sub(r'^(depois de ouvir o Plen[aá]rio,?\s*)', '', trecho.strip(' ,:-'), flags=re.I)
    trecho = trecho[:1].upper() + trecho[1:]
    if len(trecho) > limite:
        corte = trecho[:limite].rsplit(' ', 1)[0]
        trecho = corte.rstrip(',;:') + '…'
    return trecho
