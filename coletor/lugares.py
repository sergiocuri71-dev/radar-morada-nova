"""Encontra ruas, avenidas, praças, bairros e povoados citados num pedido, e o tema do pedido.
Regra única para todos os vereadores."""
import re, unicodedata

def sem_acento(t):
    return ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')

PREFIXOS = {
    'rua': 'Rua', 'r': 'Rua', 'avenida': 'Avenida', 'av': 'Avenida', 'praca': 'Praça', 'pca': 'Praça',
    'travessa': 'Travessa', 'alameda': 'Alameda',
    'bairro': 'Bairro', 'povoado': 'Povoado', 'povoados': 'Povoado', 'distrito': 'Distrito',
    'comunidade': 'Comunidade', 'vila': 'Vila', 'loteamento': 'Loteamento', 'condominio': 'Condomínio',
}
AREA = {'Bairro', 'Povoado', 'Distrito', 'Comunidade', 'Vila', 'Loteamento', 'Condomínio'}
ABREV = {'cel': 'Coronel', 'dr': 'Doutor', 'pe': 'Padre', 'prof': 'Professor', 'ver': 'Vereador', 'sr': 'Senhor', 'sta': 'Santa', 'sto': 'Santo'}
LIGA = {'de', 'do', 'da', 'dos', 'das', 'e'}
PALAVRA = r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9'’\-]*\.?"
RX = re.compile(r"\b(Rua|R\.|Avenida|Av\.|Praça|Pça\.|Travessa|Alameda|Bairros?|bairros?|Povoados?|povoados?|Distrito|distrito|Comunidade|comunidade|Vila|Loteamento|Condomínio)\s+((?:" + PALAVRA + r"\s*)+)")
# nomes que não são lugares de verdade
NAO_LUGAR = {'morada nova de minas', 'horizontal de lotes', 'empresarial', 'municipal'}

def _nome(trecho):
    """Pega as palavras do nome até a primeira palavra minúscula que não seja ligação, ou fim de frase."""
    out = []
    for tok in trecho.split():
        base = tok.rstrip('.,;:')
        chave = sem_acento(base).lower()
        if not base:
            break
        if chave in LIGA:
            out.append(chave if chave != 'e' else 'e'); continue
        if chave in ABREV and tok.endswith('.'):
            out.append(ABREV[chave]); continue
        if not (base[0].isupper() or base[0].isdigit()):
            break
        out.append(base)
        if tok.endswith(('.', ',', ';', ':')) and chave not in ABREV:
            break
    while out and out[-1] in LIGA:
        out.pop()
    # 'e' no meio costuma separar dois lugares ("Guará I e Guará II"): corta
    if 'e' in out:
        out = out[:out.index('e')]
    return ' '.join(out)

def canonico(tipo, nome):
    n = sem_acento(nome).lower()
    n = re.sub(r'\bcel\b\.?', 'coronel', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return f"{tipo}|{n}"

def lugares(texto):
    t = re.sub(r'\s+', ' ', texto or '')
    achados = []
    for m in RX.finditer(t):
        pref = sem_acento(m.group(1)).lower().rstrip('.')
        tipo = PREFIXOS.get(pref.rstrip('s') if pref not in PREFIXOS else pref)
        if not tipo:
            continue
        nome = _nome(m.group(2))
        base = re.sub(r'^(de|do|da|dos|das) ', '', sem_acento(nome).lower())
        if len(nome) < 3 or base in NAO_LUGAR or base.startswith('morada nova'):
            continue
        achados.append((tipo, nome))
    return achados

TEMAS = [
    ('quebra-molas', r'quebra-?molas|redutor(es)? de velocidade|lombada'),
    ('iluminação', r'ilumina|lampada|luminaria|poste|refletor'),
    ('calçamento, asfalto e buracos', r'calcament|asfalt|pavimenta|buraco|tapa-?buraco|bloquete|cascalh|patrol|meio-?fio|pedras? soltas'),
    ('limpeza e capina', r'limpeza|capina|rocad|varri|entulho|lixo|mato'),
    ('água, esgoto e drenagem', r'agua|esgoto|bueiro|manilha|drenagem|pluvial|alagament|enchente|fossa|poco de visita'),
    ('sinalização e trânsito', r'sinaliza|placas? (de |\W)?(transito|regulamenta|advertencia|parada|pare\b|proibido)|proibido estacionar|faixa de pedestre|sentido de circula|transito|estacionamento|mao unica|mao dupla'),
    ('estradas, pontes e mata-burros', r'estrada|ponte|mata-?burro|vicina'),
    ('árvores e poda', r'poda|arvore|arboriza'),
    ('praças, quadras e parques', r'praca|quadra|parque|academia|campo de futebol|ginasio'),
    ('saúde', r'\bubs\b|posto de saude|medic|ambulancia|consulta|exame|saude'),
    ('escolas e transporte escolar', r'escola|cemei|creche|transporte escolar|carro escolar|alunos'),
]
def tema(pedido_texto):
    t = sem_acento(pedido_texto or '').lower()[:260]
    for nome, rx in TEMAS:
        if re.search(rx, t):
            return nome
    return None

TITULOS = r'^(coronel|doutor|padre|professor|vereador|conego|dona|senhor) '
ALIAS = {'vaus das flores': 'vau das flores', 'guara i o': 'guara i'}

def _chave(tipo, nome):
    n = sem_acento(nome).lower()
    n = re.sub(r'^(de|do|da|dos|das) ', '', re.sub(r'\s+', ' ', n).strip())
    n = ALIAS.get(n, n)
    grupo = 'area' if tipo in AREA else tipo.lower()
    return grupo, n

def indexar(itens):
    """itens: lista de (id, texto). Devolve (lugares, por_item):
    lugares[chave] = {'nome': exibido, 'tipo': ..., 'ids': set}; por_item[id] = set de chaves."""
    bruto = {}
    for i, texto in itens:
        for tipo, nome in lugares(texto):
            g, n = _chave(tipo, nome)
            if len(n) < 3:
                continue
            e = bruto.setdefault((g, n), {'formas': {}, 'tipos': {}, 'ids': set()})
            limpo = re.sub(r'^(de|do|da|dos|das) ', '', nome)
            e['formas'][limpo] = e['formas'].get(limpo, 0) + 1
            e['tipos'][tipo] = e['tipos'].get(tipo, 0) + 1
            e['ids'].add(i)
    # juntar variações: sem título (Cel. Arnaldo = Arnaldo) e nome encurtado (Alceu Alves = Alceu Alves Ferreira)
    chaves = sorted(bruto)
    destino = {}
    for g, n in chaves:
        alvo = None
        sem_titulo = re.sub(TITULOS, '', n)
        candidatos = [k for k in chaves if k[0] == g and k[1] != n and
                      len(k[1]) > len(n) and
                      (re.sub(TITULOS, '', k[1]) == sem_titulo or k[1].startswith(n + ' '))]
        if len(candidatos) == 1:
            alvo = candidatos[0]
        destino[(g, n)] = alvo
    for k, alvo in destino.items():
        passos = 0
        while alvo and destino.get(alvo) and passos < 10:
            alvo = destino[alvo]; passos += 1
        if alvo and alvo != k and alvo in bruto and k in bruto:
            a, b = bruto[alvo], bruto.pop(k)
            for f, c in b['formas'].items(): a['formas'][f] = a['formas'].get(f, 0) + c
            for f, c in b['tipos'].items(): a['tipos'][f] = a['tipos'].get(f, 0) + c
            a['ids'] |= b['ids']
    # segunda passada: áreas citadas sem a palavra "bairro"/"povoado" ("no Vau das Flores", "em Cacimbas")
    for (g, n), e in bruto.items():
        if g != 'area' or len(n) < 5:
            continue
        rx = re.compile(r'(?<!rua )(?<!avenida )(?<!av\. )\b' + re.escape(n) + r'\b')
        for i, texto in itens:
            if rx.search(sem_acento(re.sub(r'\s+', ' ', texto or '')).lower()):
                e['ids'].add(i)
    lugares_ = {}
    por_item = {}
    for (g, n), e in bruto.items():
        chave = f"{g}:{n}"
        tipo = max(e['tipos'], key=e['tipos'].get)
        nome = max(e['formas'], key=lambda f: (e['formas'][f], sum(ch != c for ch, c in zip(f, sem_acento(f)))))
        lugares_[chave] = {'nome': nome, 'tipo': tipo, 'ids': e['ids']}
        for i in e['ids']:
            por_item.setdefault(i, set()).add(chave)
    return lugares_, por_item
