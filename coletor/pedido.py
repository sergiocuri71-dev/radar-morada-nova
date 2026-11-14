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

import unicodedata
def _sa(t):
    return ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn').lower()

def autores(texto, nomes, autor_registrado):
    """Quem assina: nomes de vereadores no cabeçalho, antes de 'vereador(es) desta Casa'.
    Ex.: 'DOUGLAS MIGUEL ... e MUNIQUE PRISCILA DA SILVA, vereadores desta Casa, vêm...'"""
    t = _sa(re.sub(r'\s+', ' ', texto or ''))
    m = re.search(r'senhor presidente,?(.{0,400}?),?\s*vereador(?:a|es|as)? (?:desta|dessa|da) casa', t)
    achados = []
    if m:
        cab = m.group(1)
        for n in nomes:
            partes = _sa(n).split()
            # nome completo, ou primeiro + último nome
            if _sa(n) in cab or (partes[0] in cab and partes[-1] in cab):
                if n not in achados:
                    achados.append(n)
    # ordem de assinatura no documento
    if m:
        achados.sort(key=lambda n: cab.find(_sa(n).split()[0]))
    return achados or [autor_registrado]
