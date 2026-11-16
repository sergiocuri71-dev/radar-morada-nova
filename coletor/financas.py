"""Receitas e despesas da Prefeitura (município) e da Câmara, a partir dos relatórios fiscais oficiais
que o município entrega ao Tesouro Nacional (Siconfi). API pública, sem cadastro.
Uso: python3 financas.py dados/financas.json"""
import datetime, json, os, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from detalhe_gastos import montar as montar_detalhe

SICONFI = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
IBGE = 3143500  # Morada Nova de Minas
FUNCOES = ["Legislativa", "Judiciária", "Essencial à Justiça", "Administração", "Defesa Nacional", "Segurança Pública",
           "Relações Exteriores", "Assistência Social", "Previdência Social", "Saúde", "Trabalho", "Educação", "Cultura",
           "Direitos da Cidadania", "Urbanismo", "Habitação", "Saneamento", "Gestão Ambiental", "Ciência e Tecnologia",
           "Agricultura", "Organização Agrária", "Indústria", "Comércio e Serviços", "Comunicações", "Energia",
           "Transporte", "Desporto e Lazer", "Encargos Especiais"]
MESES_BIMESTRE = {1: "jan–fev", 2: "jan–abr", 3: "jan–jun", 4: "jan–ago", 5: "jan–out", 6: "jan–dez"}

def get(rota, **params):
    url = f"{SICONFI}/{rota}?" + urllib.parse.urlencode(params)
    for i in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RadarMoradaNova/0.1 (projeto civico)"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8")).get("items", []), url
        except Exception:
            if i == 4:
                raise
            time.sleep(10 * (i + 1))

def valor(itens, anexo, conta_inicio, coluna_inicio):
    for x in itens:
        if x["anexo"] == anexo and x["conta"].startswith(conta_inicio) and x["coluna"].startswith(coluna_inicio):
            return x["valor"]
    return None

def ultimo_periodo(ano, entregavel):
    itens, _ = get("extrato_entregas", id_ente=IBGE, an_referencia=ano)
    ps = [int(x["periodo"]) for x in itens if x.get("entregavel") == entregavel]
    return max(ps) if ps else None

def rreo(ano, bim):
    itens, url = get("rreo", an_exercicio=ano, nr_periodo=bim, co_tipo_demonstrativo="RREO Simplificado", id_ente=IBGE)
    if not itens:
        return None
    a1, a2 = "RREO-Anexo 01", "RREO-Anexo 02"
    funcoes = []
    for f in FUNCOES:
        emp = valor(itens, a2, f, "DESPESAS EMPENHADAS ATÉ O BIMESTRE")
        if emp is None:
            continue
        funcoes.append({"funcao": f,
                        "dotacao": valor(itens, a2, f, "DOTAÇÃO ATUALIZADA"),
                        "empenhado": emp,
                        "liquidado": valor(itens, a2, f, "DESPESAS LIQUIDADAS ATÉ O BIMESTRE")})
    rec, desp = "RECEITAS (EXCETO INTRA", "DESPESAS (EXCETO INTRA"
    return {
        "ano": ano, "bimestre": bim, "meses": MESES_BIMESTRE[bim], "fonte": url,
        "receita_prevista": valor(itens, a1, rec, "PREVISÃO ATUALIZADA"),
        "receita_realizada": valor(itens, a1, rec, "Até o Bimestre"),
        "despesa_autorizada": valor(itens, a1, desp, "DOTAÇÃO ATUALIZADA"),
        "despesa_empenhada": valor(itens, a1, desp, "DESPESAS EMPENHADAS ATÉ O BIMESTRE"),
        "despesa_liquidada": valor(itens, a1, desp, "DESPESAS LIQUIDADAS ATÉ O BIMESTRE"),
        "despesa_paga": valor(itens, a1, desp, "DESPESAS PAGAS ATÉ O BIMESTRE"),
        "funcoes": sorted(funcoes, key=lambda f: -(f["liquidado"] or 0)),
    }

def dca(ano):
    """Balanço anual (DCA): o documento definitivo de um ano já fechado."""
    rec, url = get("dca", an_exercicio=ano, no_anexo="DCA-Anexo I-C", id_ente=IBGE)
    desp, _ = get("dca", an_exercicio=ano, no_anexo="DCA-Anexo I-D", id_ente=IBGE)
    func, _ = get("dca", an_exercicio=ano, no_anexo="DCA-Anexo I-E", id_ente=IBGE)
    if not (rec and desp and func):
        return None
    linha = [x for x in rec if x["conta"].startswith("RECEITAS (EXCETO INTRA")]
    brutas = sum(x["valor"] for x in linha if x["coluna"].startswith("Receitas Brutas"))
    deducoes = sum(x["valor"] for x in linha if x["coluna"].startswith(("Deduções", "Outras Deduções")))
    total = lambda col: next((x["valor"] for x in desp if x["conta"] == "Total Geral da Despesa" and x["coluna"] == col), None)
    funcoes = {}
    for x in func:
        m = re.match(r"^(\d{2}) - (.+)$", x["conta"])
        if m:
            e = funcoes.setdefault(m.group(2), {"funcao": m.group(2)})
            chave = {"Despesas Empenhadas": "empenhado", "Despesas Liquidadas": "liquidado", "Despesas Pagas": "pago"}.get(x["coluna"])
            if chave:
                e[chave] = x["valor"]
    return {"ano": ano, "fonte": url, "receita_bruta": brutas, "receita_realizada": brutas - deducoes,
            "despesa_empenhada": total("Despesas Empenhadas"), "despesa_liquidada": total("Despesas Liquidadas"),
            "despesa_paga": total("Despesas Pagas"),
            "funcoes": sorted(funcoes.values(), key=lambda f: -(f.get("liquidado") or 0))}

def rgf(ano, sem, poder):
    itens, url = get("rgf", an_exercicio=ano, in_periodicidade="S", nr_periodo=sem,
                     co_tipo_demonstrativo="RGF Simplificado", co_poder=poder, id_ente=IBGE)
    if not itens:
        return None
    a = "RGF-Anexo 01"
    return {"ano": ano, "semestre": sem, "fonte": url,
            "pessoal_12m": valor(itens, a, "DESPESA TOTAL COM PESSOAL", "Valor"),
            "pessoal_pct": valor(itens, a, "DESPESA TOTAL COM PESSOAL", "% sobre"),
            "limite_pct": valor(itens, a, "LIMITE MÁXIMO", "% sobre"),
            "limite_valor": valor(itens, a, "LIMITE MÁXIMO", "Valor"),
            "rcl": valor(itens, a, "RECEITA CORRENTE LIQUIDA", "Valor")}

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

def detalhe(ano, mes):
    """Gasto por área, setor e tipo de despesa até o fim do mês (Matriz de Saldos Contábeis)."""
    itens, url = get("msc_orcamentaria", id_ente=IBGE, an_referencia=ano, me_referencia=mes,
                     co_tipo_matriz="MSCC", classe_conta=6, id_tv="ending_balance")
    if not itens:
        return None
    d = montar_detalhe(itens)
    d.update({"ano": ano, "mes": mes, "ate": MESES[mes - 1], "fonte": url})
    return d

def mais_recente(fn, entregavel):
    ano = datetime.date.today().year
    for a in (ano, ano - 1):
        p = ultimo_periodo(a, entregavel)
        if p:
            r = fn(a, p)
            if r:
                return r
    return None

def main(saida):
    atual = mais_recente(rreo, "Relatório Resumido de Execução Orçamentária Simplificado")
    # ano fechado: balanço anual (definitivo); se ainda não saiu, o último relatório bimestral do ano
    anterior = None
    if atual:
        anterior = dca(atual["ano"] - 1)
        if anterior:
            anterior["tipo"] = "balanço anual"
        else:
            anterior = rreo(atual["ano"] - 1, 6)
            if anterior:
                anterior["tipo"] = "relatório do 6º bimestre"
    # detalhe por área no mesmo período do relatório bimestral (fim do bimestre), para os totais baterem
    if atual:
        try:
            atual["detalhe"] = detalhe(atual["ano"], atual["bimestre"] * 2)
        except Exception as e:
            print(f"AVISO: detalhe dos gastos indisponível ({e})")
    dados = {
        "coletado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "municipio": {"atual": atual, "ano_anterior": anterior},
        "camara_pessoal": mais_recente(lambda a, s: rgf(a, s, "L"), "Relatório de Gestão Fiscal Simplificado"),
        "prefeitura_pessoal": mais_recente(lambda a, s: rgf(a, s, "E"), "Relatório de Gestão Fiscal Simplificado"),
    }
    assert atual and atual["receita_realizada"] and atual["funcoes"], "RREO incompleto"
    json.dump(dados, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("ok: RREO", atual["ano"], "bim", atual["bimestre"], "| funções", len(atual["funcoes"]),
          "| RGF Câmara", (dados["camara_pessoal"] or {}).get("pessoal_pct"), "%")

if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except Exception as e:
        import os
        if os.path.exists(sys.argv[1]):
            print(f"AVISO: finanças não atualizadas ({e}). Mantida a última versão boa.")
        else:
            raise
