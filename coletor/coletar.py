"""Coleta os dados oficiais da Câmara Municipal de Morada Nova de Minas (API Syssolution).
Gera data.json. Uso: python3 coletar.py saida/data.json"""
import json, sys, time, urllib.request, datetime

BASE = "https://api.syssolution.com.br"
SITE = "https://camaramoradanova.mg.gov.br"
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

def paginado(caminho_fmt):
    itens, pg = [], 1
    while True:
        d = api(caminho_fmt.format(pg=pg))
        itens += d.get("data") or []
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
    assert len(vereadores) >= 9, "menos vereadores que o esperado"
    assert len(props) >= 100, "poucas proposições: coleta suspeita"
    assert len(projetos) >= 50, "poucos projetos: coleta suspeita"
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False)
    print(f"ok: {len(vereadores)} vereadores, {len(props)} proposições, {len(projetos)} projetos, {len(votacoes)} votações")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data.json")
