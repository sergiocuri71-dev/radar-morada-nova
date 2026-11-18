"""Baixa as atas (PDF escaneado), faz OCR e extrai as ausências de vereadores.
Uso: python3 atas.py pasta_cache saida/ausencias.json
Precisa de: pdftoppm (poppler-utils) e tesseract com o idioma 'por'."""
import json, os, re, subprocess, sys, unicodedata, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from coletar import api, HEADERS
from cidades import C

CDN = f"https://cdn.syssolution.com.br/{C['cdn']}/Sessoes/"

def sa(t):
    return ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn').lower()

def ocr(link, cache):
    txt = os.path.join(cache, link[:-4] + ".txt")
    if os.path.exists(txt) and os.path.getsize(txt) > 0:
        return open(txt, encoding="utf-8").read()
    pdf = os.path.join(cache, link)
    req = urllib.request.Request(CDN + link, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r, open(pdf, "wb") as f:
        f.write(r.read())
    base = os.path.join(cache, link[:-4])
    subprocess.run(["pdftoppm", "-r", "200", "-gray", "-png", pdf, base], check=True)
    paginas = sorted(p for p in os.listdir(cache) if p.startswith(os.path.basename(base) + "-") and p.endswith(".png"))
    texto = ""
    for p in paginas:
        texto += subprocess.run(["tesseract", os.path.join(cache, p), "-", "-l", "por"],
                                capture_output=True, text=True).stdout + "\n"
        os.remove(os.path.join(cache, p))
    open(txt, "w", encoding="utf-8").write(texto)
    return texto

# como cada vereador costuma aparecer escrito nas atas (Morada Nova: lista conferida à mão)
APELIDOS_MORADA = {
    "Carlos Antônio Ribeiro": ["carlos antonio", "kitute"],
    "Diney Francisco da Silva": ["diney"],
    "Douglas Miguel Gomes de Moura Batista": ["douglas", "guel"],
    "Luiz Carlos de Oliveira": ["luiz carlos"],
    "Lyncoln Bryan Silva Teixeira": ["lyncoln"],
    "Munique Priscila da Silva": ["munique"],
    "Onezio Ferreira Maia": ["onezio"],
    "Osvaldo Alvares da Silva Neto": ["osvaldo", "netinho"],
    "Washington Rogerio Guimaraes": ["washington"],
}
APELIDOS = APELIDOS_MORADA

def apelidos_automaticos(data_json):
    """Para as outras cidades: primeiro e segundo nome e o nome parlamentar de cada vereador atual."""
    out = {}
    for v in json.load(open(data_json, encoding="utf-8"))["vereadores"]:
        partes, n = [], 0
        for p in sa(v["nome"]).split():  # primeiro e segundo nome, com o "de/do/da" do meio se houver
            partes.append(p)
            n += p not in ("de", "do", "da", "dos", "das", "e")
            if n == 2:
                break
        chaves = {re.escape(" ".join(partes))}
        todas = [p for p in sa(v["nome"]).split() if p not in ("de", "do", "da", "dos", "das", "e")]
        if len(todas) >= 3:  # primeiro nome + último sobrenome, com o meio abreviado ("jessica a. cunha morais")
            chaves.add(re.escape(todas[0]) + r"(?:\s+\S+){0,3}?\s+" + re.escape(todas[-1]))
        ap = sa((v.get("apelido") or "").strip())
        ap = re.sub(r"^(vereador[a]?|ver\.?)\s+", "", ap).strip()
        if len(ap) >= 4:
            chaves.add(re.escape(ap))
        out[v["nome"]] = sorted(c for c in chaves if c)
    return out

FIM_FRASE = re.compile(r'(?<![\s.][a-z])\.\s')
PLENARIO = re.compile(r'reuni[aã]o (ordin|extraord|audi)|^ata da ?\d|audi[eê]ncia', re.I)

def ausencias(texto):
    """Só frases do tipo "Ausente(s) o(s) vereador(es) X..." ou "ausência do vereador X".
    Os nomes têm de vir logo depois, na mesma frase."""
    t = sa(re.sub(r'\s+', ' ', texto))
    achados = {}
    rx = re.compile(r'(ausentes?\s+(?:(?:o|a|os|as)\s+)?(?:[^a-z\s]{1,4}\s*)?(?:senhor(?:es)?\s+|senhora\s+)?vereador\w*|ausencia\s+d[oa]s?\s+vereador\w*|nao\s+comparec\w+\s+(?:o|a|os|as)\s+(?:ver\.?s?|vereador\w*))')
    for m in rx.finditer(t):
        f = FIM_FRASE.search(t, m.end())  # fim da frase, sem cortar em abreviação ("carlos l. franca")
        fim = f.start() if f else -1
        nomes = t[m.end(): fim if fim > 0 else m.end() + 200]
        antes = t[max(0, t.rfind('. ', 0, m.start()) + 2, m.start() - 120):m.start()]
        justificada = bool(re.search(r'justific|abonad|motivo de saude|compromisso|comunicou', antes + nomes))
        for nome, chaves in APELIDOS.items():
            if any(re.search(r'\b' + c + r'\b', nomes) for c in chaves):
                achados[nome] = achados.get(nome, False) or justificada
    return achados

def main(cache, saida):
    global APELIDOS
    os.makedirs(cache, exist_ok=True)
    if C["slug"] != "morada-nova-de-minas":
        APELIDOS = apelidos_automaticos(os.path.join(os.path.dirname(saida), "data.json"))
    lista = api("/portal/reuniao/Atas")
    reunioes = []
    for a in sorted(lista, key=lambda x: x["data"]):
        if not PLENARIO.search(a["nome"]) or re.search(r'comiss|posse|solene|elei|especial', a["nome"], re.I):
            continue
        if C.get("desde") and int(a["data"][:4]) < C["desde"]:
            continue
        if not re.fullmatch(r"[\w.\-]+\.pdf", a.get("link") or "", re.I):
            continue  # algumas Câmaras põem vídeo do YouTube no lugar do PDF da ata
        try:
            texto = ocr(a["link"], cache)
        except Exception as e:
            print(f"AVISO: ata {a['link']} não lida ({e})")
            continue
        d = a["data"]
        reunioes.append({"data": f"{d[8:]}/{d[5:7]}/{d[:4]}", "nome": a["nome"].strip(),
                         "url": CDN + a["link"], "ausentes": ausencias(texto),
                         "texto": sa(re.sub(r'\s+', ' ', texto))})
    json.dump({"reunioes": reunioes}, open(saida, "w", encoding="utf-8"), ensure_ascii=False)
    print("ok", len(reunioes), "atas de reuniões")

if __name__ == "__main__":
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception as e:
        # Se a Câmara estiver fora do ar, mantém a última leitura boa das atas em vez de travar a publicação.
        if os.path.exists(sys.argv[2]):
            print(f"AVISO: não foi possível atualizar as atas ({e}). Mantida a última leitura boa.")
        else:
            raise
