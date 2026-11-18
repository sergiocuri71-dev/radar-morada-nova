"""Coleta os dados oficiais da Câmara Municipal de Morada Nova de Minas (API Syssolution).
Gera data.json. Uso: python3 coletar.py saida/data.json"""
import json, os, re, sys, time, urllib.request, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cidades import C

BASE = "https://api.syssolution.com.br"
SITE = C["camara"]
DESDE = C.get("desde")  # se definido, só coleta o que é deste ano em diante
HEADERS = {"Origin": SITE, "Referer": SITE + "/",
           "User-Agent": "RadarMoradaNova/0.1 (projeto civico, coleta lenta)"}
PAUSA = 0.7  # segundos entre chamadas, para não pesar no servidor

def api(caminho, tentativas=5):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(BASE + caminho, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=40) as r:
                dado = json.loads(r.read().decode("utf-8"))
            time.sleep(PAUSA)
            if isinstance(dado, dict) and str(dado.get("statusDescriptor", "")).startswith(("4", "5")):
                raise RuntimeError(dado["statusDescriptor"])
            return dado
        except Exception as e:
            if i == tentativas - 1:
                raise
            time.sleep(10 * (i + 1))

def ano_de(x):
    for k in ("ano",):
        if str(x.get(k) or "").isdigit():
            return int(x[k])
    m = re.search(r"(\d{4})", str(x.get("data") or x.get("data_recebimento") or ""))
    return int(m.group(1)) if m else 9999

def paginado(caminho_fmt):
    """Lê todas as páginas. Com DESDE, guarda só o que é recente e para quando
    uma página inteira já é anterior a DESDE (as listas vêm da mais nova para a mais antiga)."""
    itens, pg = [], 1
    while True:
        d = api(caminho_fmt.format(pg=pg))
        pagina = d.get("data") or []
        if DESDE:
            novos = [x for x in pagina if ano_de(x) >= DESDE]
            itens += novos
            if pagina and not novos:
                return itens
        else:
            itens += pagina
        if pg >= int(d.get("totalPaginas") or 1):
            return itens
        pg += 1

def main(saida):
    vereadores = api("/portal/vereadores/listar")["data"]
    for v in vereadores:
        perfil = api(f"/portal/vereadores/recuperar/{v['id']}")
        v["apelido"] = perfil.get("parlamentar")
        v["email"] = (perfil.get("email") or "").strip()  # contato publicado pela Câmara na ficha oficial
        v["telefone_gabinete"] = (perfil.get("telefone_gabinete") or "").strip()
        v["estatisticas"] = api(f"/portal/vereadores/estatisticas/{v['id']}")
    props = paginado("/portal/proposicoes/listar/100/{pg}/")
    for p in props:
        det = api(f"/portal/proposicoes/{p['id']}")
        p["texto_completo"] = det.get("texto") or p.get("texto") or ""
        ev = api(f"/portal/proposicoes/eventos/{p['id']}")
        p["eventos"] = ev.get("data") if isinstance(ev, dict) else ev
    projetos = paginado("/portal/projeto/listar/100/{pg}/todos/todos/todos/todos/todos/todos")
    votacoes = []
    for aba in ("proposicoes", "projetos"):
        for x in paginado("/portal/votacoes/" + aba + "/100/{pg}//"):
            x["aba"] = aba
            votacoes.append(x)
    dados = {
        "coletado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "fonte": SITE,
        "vereadores": vereadores,
        "proposicoes": props,
        "votacoes": votacoes,
        "projetos": projetos,
    }
    # checagem mínima: não gravar coleta incompleta
    assert len(vereadores) >= C["min_vereadores"], "menos vereadores que o esperado"
    assert len(props) >= C["min_props"], "poucas proposições: coleta suspeita"
    assert len(projetos) >= C["min_projetos"], "poucos projetos: coleta suspeita"
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False)
    print(f"ok: {len(vereadores)} vereadores, {len(props)} proposições, {len(projetos)} projetos, {len(votacoes)} votações")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data.json")
