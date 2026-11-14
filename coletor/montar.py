"""Monta a página a partir de dados/data.json e dados/ausencias.json (dados oficiais da Câmara).
Uso: python3 montar.py dados site/index.html"""
import json, re, sys, os, datetime
sys.path.insert(0, os.path.dirname(__file__))
from pedido import pedido, autores
from lugares import indexar, tema
from classificar import classificar_proposicao, classificar_projeto, GRUPOS, EXPLICA

SITE = "https://camaramoradanova.mg.gov.br"
raiz = sys.argv[1] if len(sys.argv) > 1 else "dados"          # onde estão data.json e ausencias.json
saida = sys.argv[2] if len(sys.argv) > 2 else f"{raiz}/index.html"  # onde gravar a página
d = json.load(open(f"{raiz}/data.json", encoding="utf-8"))

def resumo(t):
    r = pedido(t)
    return re.sub(r'\s*Nestes termos,?\s*[Pp]ede deferimento\.?\s*$', '', r).strip()

vereadores = []
for v in d["vereadores"]:
    sigla = v["partido"].split(" - ")[-1].strip() if " - " in v["partido"] else v["partido"].strip()
    vereadores.append({
        "id": v["id"], "nome": v["nome"], "apelido": (v.get("apelido") or "").strip(),
        "cargo": re.sub(r'\s+', ' ', v["cargo"]).strip(), "partido": v["partido"].strip(), "sigla": sigla,
        "presenca": v["estatisticas"].get("presenca"),
        "oficialProp": sum(x["quantia"] for x in v["estatisticas"].get("proposicoes", [])),
        "url": f"{SITE}/vereador/{v['id']}",
    })
nomes = {v["nome"] for v in d["vereadores"]}
lista_nomes = sorted(nomes)
props = []
for p in d["proposicoes"]:
    props.append({
        "grupo": classificar_proposicao(p["tipo"], pedido(p.get("texto_completo") or p.get("texto") or "", 3000)),
        "id": p["id"], "tipo": p["tipo"].strip().capitalize().replace("Indicação", "Indicação"),
        "numero": p["numero"], "ano": p["ano"], "data": p["data"], "autor": p["autoria"],
        "autores": autores(p.get("texto_completo") or "", lista_nomes, p["autoria"]),
        "dest": (p.get("destinatario") or "").strip(), "pedido": resumo(p.get("texto_completo") or p.get("texto")),
        "url": f"{SITE}/Proposicao/{p['id']}",
    })
for x in d.get("projetos", []):
    if x["autoria"] not in nomes or int(x["ano"]) < 2025:
        continue  # Executivo e Mesa Diretora não entram na conta de um vereador
    assunto = re.sub(r'\s+', ' ', re.sub(r'["“”]', '', x.get("assunto") or "")).strip().rstrip('.').strip() + '.'
    props.append({
        "grupo": classificar_projeto(x["tipo"], assunto), "id": x["cod"], "tipo": x["tipo"],
        "numero": x["numero"], "ano": x["ano"], "data": x["data_recebimento"], "autor": x["autoria"],
        "autores": [x["autoria"]] + [c for c in (x.get("coautores") or []) if isinstance(c, str) and c in nomes],
        "dest": "", "pedido": assunto[:1].upper() + assunto[1:].lower() if assunto.isupper() else assunto,
        "url": f"{SITE}/Projeto/{x['cod']}", "projeto": True,
    })
# Passo 4: lugares citados e tema de cada pedido (só requerimentos, indicações e moções)
textos = {p["id"]: pedido(p.get("texto_completo") or p.get("texto") or "", 5000) for p in d["proposicoes"]}
mapa_lugares, por_item = indexar(list(textos.items()))
for p in props:
    if p.get("projeto"):
        continue
    p["lugares"] = sorted(por_item.get(p["id"], []))
    p["tema"] = tema(textos[p["id"]])
    p["busca"] = textos[p["id"]][:1500]
rep = {}
for p in props:
    if not p.get("tema"):
        continue
    for k in p.get("lugares", []):
        rep.setdefault((k, p["tema"]), []).append(p["id"])
repetidos = sorted(([k, t, ids] for (k, t), ids in rep.items() if len(ids) >= 2), key=lambda x: (-len(x[2]), x[0]))
lugares_saida = {k: {"nome": v["nome"], "tipo": v["tipo"]} for k, v in mapa_lugares.items()}
pedido_por_id = {p["id"]: p["pedido"] for p in props}
votacoes, vistos = [], {}
for x in d["votacoes"]:
    chave = (x["id"], x["data"], json.dumps(x["votos"], sort_keys=True))
    if chave in vistos:  # a Câmara às vezes publica a mesma votação repetida, idêntica
        vistos[chave]["repeticoes"] += 1
        continue
    votacoes.append({
        "id": x["id"], "titulo": x["titulo"], "data": x["data"], "sessao": x.get("sessao"),
        "resultado": x.get("resultado"), "totais": x["totais"],
        "ementa": pedido_por_id.get(x["id"]) or resumo(x.get("ementa") or "") if x["link"] == "proposicao" else re.sub(r'\s+', ' ', re.sub(r'["“”]', '', x.get("ementa") or "")).strip(),
        "votos": [{"v": y["vereador"], "voto": y["voto"]} for y in x["votos"]],
        "url": f"{SITE}/{'Proposicao' if x['link']=='proposicao' else 'Projeto'}/{x['id']}",
        "repeticoes": 1,
    })
    vistos[chave] = votacoes[-1]
# Passo 5: ausências registradas nas atas e votações que não batem com a ata do dia
atas = []
if os.path.exists(f"{raiz}/ausencias.json"):
    atas = json.load(open(f"{raiz}/ausencias.json", encoding="utf-8"))["reunioes"]
ata_do_dia = {}
for a in atas:
    ata_do_dia.setdefault(a["data"], []).append(a)
for v in vereadores:
    v["ausencias"] = [{"data": a["data"], "nome": a["nome"], "url": a["url"], "justificada": a["ausentes"][v["nome"]]}
                      for a in atas if v["nome"] in a["ausentes"]]
nome_por_id = {v["id"]: v["nome"] for v in vereadores}
for x in votacoes:
    do_dia = ata_do_dia.get(x["data"])
    if not do_dia:
        continue
    texto = " ".join(a["texto"] for a in do_dia)
    ausentes = set().union(*[a["ausentes"].keys() for a in do_dia])
    m = re.match(r"\D+?\s*(\d+)/(\d+)", x["titulo"])
    problemas = []
    if m and not re.search(r"\b0*" + m.group(1) + r"\s*/\s*" + m.group(2), texto):
        problemas.append("a ata desta reunião não cita esta proposta")
    votou_ausente = [nome_por_id.get(y["v"], "") for y in x["votos"] if y["voto"] not in ("ausente",) and nome_por_id.get(y["v"]) in ausentes]
    if votou_ausente:
        problemas.append("a ata registra como ausente quem aparece votando: " + ", ".join(votou_ausente))
    if m and int(m.group(2)) < 2025:
        problemas.insert(0, f"o projeto é de {m.group(2)}, da legislatura anterior, mas a votação aparece com data de {x['data']} e com os votos dos vereadores atuais, vários dos quais não eram vereadores em {m.group(2)}")
    if problemas:
        x["conflito"] = "; ".join(problemas)
coletado = datetime.datetime.fromisoformat(d["coletado_em"]).astimezone(datetime.timezone(datetime.timedelta(hours=-3)))
repo = os.environ.get("GITHUB_REPOSITORY", "")
dados = {"repo": repo, "atualizado": coletado.strftime("%d/%m/%Y às %H:%M"), "site": SITE,
         "vereadores": vereadores, "props": props, "votacoes": votacoes, "totalAtas": len(atas),
         "lugares": lugares_saida, "repetidos": repetidos,
         "grupos": [{"id": k, "nome": GRUPOS[k], "explica": EXPLICA[k]} for k in GRUPOS]}
tpl = open(os.path.join(os.path.dirname(__file__), "modelo.html"), encoding="utf-8").read()
js = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
os.makedirs(os.path.dirname(saida) or ".", exist_ok=True)
open(saida, "w", encoding="utf-8").write(tpl.replace("/*DADOS*/null", js))
print("ok", len(vereadores), len(props), len(votacoes))
