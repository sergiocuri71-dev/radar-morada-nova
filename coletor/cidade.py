"""Informações da cidade: números do IBGE (SIDRA) e telefones úteis publicados pela Câmara.
Uso: python3 cidade.py dados/cidade.json"""
import datetime, html, json, os, re, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from coletar import api, SITE
from cidades import C

IBGE = C["ibge"]
SIDRA = "https://apisidra.ibge.gov.br/values"

def sidra(caminho):
    url = SIDRA + caminho
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RadarMG/0.1 (projeto civico)"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))[1:], url
        except Exception:
            if i == 3:
                raise
            time.sleep(15 * (i + 1))

def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def numeros():
    out = {}
    linhas, url = sidra(f"/t/4714/n6/{IBGE}/v/93,6318,614/p/2022")
    for x in linhas:
        chave = {"93": "populacao_2022", "6318": "area_km2", "614": "densidade"}.get(x["D2C"])
        if chave:
            out[chave] = num(x["V"])
    out["fonte_censo"] = url
    linhas, url = sidra(f"/t/6579/n6/{IBGE}/v/9324/p/last")
    if linhas:
        out["populacao_estimada"], out["ano_estimativa"], out["fonte_estimativa"] = num(linhas[0]["V"]), linhas[0]["D3N"], url
    linhas, url = sidra(f"/t/5938/n6/{IBGE}/v/37/p/last")
    if linhas:
        out["pib_mil_reais"], out["ano_pib"], out["fonte_pib"] = num(linhas[0]["V"]), linhas[0]["D3N"], url
    # tilápia: produção do município e posição em Minas e no Brasil
    linhas, url = (sidra(f"/t/3940/n6/{IBGE}/v/4146/p/last/c654/32877") if C.get("tilapia") else ([], None))
    if linhas:
        out["tilapia_kg"], out["ano_tilapia"], out["fonte_tilapia"] = num(linhas[0]["V"]), linhas[0]["D3N"], url
        for nivel, chave in (("in%20n3%2031", "tilapia_pos_mg"), ("all", "tilapia_pos_br")):
            todos, _ = sidra(f"/t/3940/n6/{nivel}/v/4146/p/last/c654/32877")
            vals = sorted(((num(x["V"]) or 0, x["D1C"]) for x in todos), reverse=True)
            out[chave] = next((i + 1 for i, (_, c) in enumerate(vals) if c == IBGE), None)
    linhas, url = sidra(f"/t/9923/n10/in%20n6%20{IBGE}/v/93/p/2022")
    out["distritos"] = [{"nome": x["D1N"].split(" - ")[0], "populacao": num(x["V"])} for x in linhas if x.get("D4N", "Total") == "Total"]
    out["fonte_distritos"] = url
    return out

CATEGORIAS = [
    ("Saúde", r"hospital|psf|ubs|caps|odontol|farmacinha|epidemiolog|tfd|apae"),
    ("Segurança e emergência", r"pol[ií]cia|delegacia|guarda municipal|conselho tutelar|bombeiro"),
    ("Educação", r"escola|cemei|creche|secretaria de educa"),
    ("Assistência social", r"cras|creas|cadastro [úu]nico|abrigo|scfv|assist[êe]ncia social|terceira idade|vila vicentina"),
    ("Prefeitura e Câmara", r"prefeit|c[âa]mara municipal|secretaria|fiscais|ilumina[çc][ãa]o p[úu]blica|impas|gabinete"),
    ("Justiça e cartórios", r"f[óo]rum|cart[óo]rio"),
    ("Serviços públicos", r"copasa|correios|emater|codevasf|rodovi[áa]ria|t[áa]xi|receiota|receita|sebrae|sindicato"),
]

def telefones():
    d = api(f"/portal/transparencia/recuperar/{C['telefones_id']}")
    t = re.sub(r"</p>", "\n", d.get("descricao") or "")
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    itens = []
    for linha in t.split("\n"):
        linha = re.sub(r"\s+", " ", linha).strip()
        m = re.match(r"^(.+?)\s+-\s+(\(?\d.*)$", linha)
        if not m:
            continue
        nome, fone = m.group(1).strip(), m.group(2).strip()
        cat = next((c for c, rx in CATEGORIAS if re.search(rx, nome, re.I)), "Outros")
        itens.append({"nome": nome, "fone": fone, "categoria": cat})
    return itens

def main(saida):
    anterior = json.load(open(saida, encoding="utf-8")) if os.path.exists(saida) else {}
    dados = {"coletado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    try:
        dados["numeros"] = numeros()
    except Exception as e:
        print(f"AVISO: IBGE indisponível ({e}); mantidos os números anteriores.")
        dados["numeros"] = anterior.get("numeros")
    try:
        if not C.get("telefones_id"):
            raise RuntimeError("sem lista de telefones configurada")
        tel = telefones()
        dados["telefones"] = tel if len(tel) >= 20 else anterior.get("telefones")
    except Exception as e:
        print(f"AVISO: telefones não atualizados ({e}); mantida a lista anterior.")
        dados["telefones"] = anterior.get("telefones")
    if C.get("telefones_id"):
        dados["fonte_telefones"] = f"{SITE}/transparencia/{C['telefones_id']}"
    if C.get("balsas"):
        dados["balsas"] = C["balsas"]
    if not dados["numeros"] and not dados["telefones"]:
        raise SystemExit("nada coletado")
    json.dump(dados, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = dados["numeros"] or {}
    print("ok: população", n.get("populacao_2022"), "| tilápia", n.get("tilapia_kg"), "pos BR", n.get("tilapia_pos_br"),
          "| telefones", len(dados["telefones"] or []))

if __name__ == "__main__":
    main(sys.argv[1])
