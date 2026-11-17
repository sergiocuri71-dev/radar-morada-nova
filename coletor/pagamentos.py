"""Quem recebeu o dinheiro: pagamentos e compras (empenhos) da Prefeitura e da Câmara,
lidos da área de Dados Abertos dos portais de transparência (sistema Memory).
Pessoa física aparece só pelo cargo ou tipo de serviço, nunca pelo nome.
Uso: python3 pagamentos.py dados/pagamentos.json dados/empenhos_cache.json"""
import collections, concurrent.futures, datetime, json, os, re, sys, time, unicodedata, urllib.request

API = "https://publico.memory.com.br/openknowledge"
ENTIDADES = {"prefeitura": ("9BP6DH", 1), "camara": ("9BP6DY", 2)}
PORTAL = {"prefeitura": "https://ilai.memory.com.br/#/entidades/login/9BP6DH/1/",
          "camara": "https://ilai.memory.com.br/#/entidades/login/9BP6DY/2/"}
FUNCOES = {"01": "Legislativa", "02": "Judiciária", "03": "Essencial à Justiça", "04": "Administração",
    "06": "Segurança Pública", "08": "Assistência Social", "09": "Previdência Social", "10": "Saúde", "11": "Trabalho",
    "12": "Educação", "13": "Cultura", "14": "Direitos da Cidadania", "15": "Urbanismo", "16": "Habitação",
    "17": "Saneamento", "18": "Gestão Ambiental", "19": "Ciência e Tecnologia", "20": "Agricultura",
    "22": "Indústria", "23": "Comércio e Serviços", "24": "Comunicações", "25": "Energia", "26": "Transporte",
    "27": "Desporto e Lazer", "28": "Encargos Especiais"}
UA = "RadarMoradaNova/0.1 (projeto civico)"
TOP_RECEB, TOP_COMPRAS = 15, 12

def chamar(caminho, tenant, ent, ano, extra=None, query=""):
    h = {"entidade": str(ent), "tenant-id": tenant, "exercicio": str(ano), "User-Agent": UA}
    h.update(extra or {})
    for i in range(4):
        try:
            req = urllib.request.Request(API + caminho + query, headers=h)
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if i == 3:
                raise
            time.sleep(8 * (i + 1))

def todos(caminho, tenant, ent, ano, tam=1000):
    linhas, pag = [], 1
    while True:
        d = chamar(caminho, tenant, ent, ano, query=f"?page={pag}&size={tam}")
        bloco = d.get("data") or []
        linhas += bloco
        if not bloco or len(linhas) >= (d.get("total") or 0):
            return linhas
        pag += 1

def conserta(t):
    """O portal grava acentos com a tabela errada (PRESTAÇĂO → PRESTAÇÃO)."""
    t = re.sub(r"\s+", " ", t or "").strip()
    try:
        return t.encode("cp1250").decode("cp1252")
    except Exception:
        return t

def pessoa_fisica(doc):
    return "*" in (doc or "") or len(re.sub(r"\D", "", doc or "")) == 11

EMPRESA = re.compile(r"\b(LTDA|ME|EPP|EIRELI|S/?A|SA|CIA|COMPANHIA|ASSOC\w*|INSTITUTO|MUNIC\w*|FUNDO|FUNDA\w*|BANCO|CONS[OÓ]RCIO|COOPERATIVA|"
    r"POSTO|CL[IÍ]NICA|SUPERMERCADO|MERCADO|SACOL[AÃ]O|COM[EÉ]RCIO|COMERCIAL|SERVI[CÇ]OS?|TRANSPORTES?|CAIXA|INSS|CEMIG|COPASA|FOLHA|SECRETARIA|"
    r"C[AÂ]MARA|IGREJA|PAR[OÓ]QUIA|EMPRESA|DISTRIBUI\w*|ENGENHARIA|CONSTRU\w*|SOCIEDADE|ADVOCACIA|CONTABI\w*|SISTEMAS|INFORM[AÁ]TICA|"
    r"EDITORA|GR[AÁ]FICA|HOSPITAL|CASA|LABORAT\w*|FARM[AÁ]CIA|DROGARIA|AUTO\w*|PE[CÇ]AS|MATERIA\w*|GRUPO|IND[UÚ]STRIA|AGRO\w*|TELECOM|"
    r"PROVEDOR|CENTRO|SA[UÚ]DE|CONSELHO|CONFEDERA\w*|SINDICATO|MINIST[EÉ]RIO|MARINHA|ESCOLA|COL[EÉ]GIO|UNIVERSIDADE|FACULDADE|TJMG|CREA|"
    r"TRIBUNAL|ESTADO|UNI[AÃ]O|RECEITA|LOJA|BAR|RESTAURANTE|HOTEL|POUSADA|ACADEMIA|TECNOLOGIA|SOLU[CÇ][OÕ]ES|M[OÓ]VEIS|VE[IÍ]CULOS|"
    r"COMBUST\w*|PNEUS|ELETRO\w*|IMPORTS?|ATACAD\w*|DEP[OÓ]SITO|MADEIREIRA|GAS|[OÓ]TICA|ODONTO\w*|MEDIC\w*|PRODU[CÇ][OÕ]ES|EVENTOS|"
    r"INST|PREV\w*|ASSIST\w*|SOCIAL|MUN|IMPAS|TELEMAR|TELEF\w*|ENERGIA|[AÁ]GUA|SANEAMENTO|COMPANY|SECURITY|"
    r"S[OÓ]M|BIKE|CENTRAL|NACIONAL|BRASIL|MINAS|OI|VIVO|TIM|CLARO|CORREIOS|PREFEITURA|GOVERNO|DEPARTAMENTO|AG[EÊ]NCIA|EXPRESS\w*)\b", re.I)

def eh_compra(e, nome):
    """Compra ou contrato (fica de fora a folha de pessoal e seus encargos, natureza 3.1)."""
    nat = (e.get("dotacao_orcamentaria") or "").split(".")
    return not eh_pessoa(e, nome) and not (len(nat) >= 2 and nat[-5:-3] == ["3", "1"]) and "FOLHA" not in (e.get("fornecedor_nome") or "").upper()

def eh_pessoa(e, nome_entidade):
    """Pessoa física ou microempreendedor registrado com o próprio nome: mostramos só o serviço."""
    if pessoa_fisica(e.get("fornecedor_cpf_cnpj")):
        return True
    n = conserta(e.get("fornecedor_nome"))
    if re.search(r"\d{2}\.?\d{3}\.?\d{3}|\d{11}", n):     # MEI: nome com o CNPJ ou CPF junto
        return True
    palavras = re.findall(r"[A-Za-zÀ-ÿ]+", n)
    return 3 <= len(palavras) <= 7 and not EMPRESA.search(n)

def normaliza_cargo(r):
    """Junta variações (Psicologa/Psicóloga, Técnica/Técnico de enfermagem) num rótulo neutro."""
    base = r.split(" (")[0]; resto = r[len(base):]
    k = re.sub(r"[^a-z ]", "", unicodedata.normalize("NFD", base.lower()))
    for chave, rot in [("tecnic", None), ("psicolog", "Psicólogo(a)"), ("fonoaudiolog", "Fonoaudiólogo(a)"), ("fisioterap", "Fisioterapeuta"),
                       ("nutricion", "Nutricionista"), ("farmac", "Farmacêutico(a)"), ("enfermeir", "Enfermeiro(a)"),
                       ("conselheir", "Conselheiro(a) tutelar"), ("diretor", "Diretor(a) escolar"), ("professor", "Professor(a)"),
                       ("supervisor", "Supervisor(a) escolar"), ("advoca", "Advogado(a)"), ("motorist", "Motorista"),
                       ("pediatr", "Médico(a) pediatra"), ("medic", "Médico(a)"), ("dentist", "Dentista"), ("odont", "Dentista")]:
        if chave in k:
            if chave == "tecnic":
                if "enferm" in k:
                    return "Técnico(a) de enfermagem" + resto
                continue
            return rot + resto
    b = base.lower()
    b = re.sub(r"\b(nest[ea]|ness[ea]) munic[ií]pio\b|\brota\b", "", b)
    b = re.sub(r"\bde serv\b", "de serviços", b)
    b = b.replace("çao", "ção").replace("çoes", "ções")
    b = re.sub(r"\s+", " ", b).strip()
    return b[:1].upper() + b[1:] + resto

def titulo(t):
    pequenas = {"de", "da", "do", "das", "dos", "e", "a", "o"}
    return " ".join(w if w in pequenas else w.capitalize() for w in t.lower().split())

def cargo(desc, tipo):
    """Rótulo de uma pessoa física: o cargo ou o tipo de serviço, sem nome."""
    d, t = conserta(desc).upper(), conserta(tipo).lower()
    if "diária" in t or "diaria" in t:
        if "prefeito" in t or re.search(r"DIARIA[S]? D[OA] PREFEITO", d):
            return "Prefeito (diárias de viagem)"
        if "secret" in t:
            return "Secretário(a) municipal (diárias de viagem)"
        if "vereador" in t or "VEREADOR" in d:
            return "Vereador(a) (diárias de viagem)"
        m = re.search(r"SERVIDOR[A]?\s+(?:DA\s+|DO\s+)?([A-ZÇÃÕÁÉÍÓÚÂÊÔ ]{4,40}?)\s*(?:,|\b[ÀA]S? CIDADES?\b|\bPARA\b|\bNO\b|\bNA\b|\bEM\b|$)", d)
        if m and not re.search(r"SECRETARIA|DEPARTAMENTO", m.group(1)):
            return f"{titulo(m.group(1).strip())} (diárias de viagem)"
        return "Servidor(a) (diárias de viagem)"
    if "premia" in t:
        return "Prêmio cultural ou esportivo"
    if "auxílio" in t or "auxilio" in t or "aux" in t and "financ" in t:
        if re.search(r"PACIENTE|TRATAMENTO|SA[UÚ]DE", d):
            return "Auxílio a paciente em tratamento"
        if "ATLETA" in d:
            return "Auxílio a atletas"
        return "Auxílio financeiro a pessoa"
    if "aliment" in t:
        return "Produtor(a) rural (alimentos)"
    if "locação de imóveis" in t or "locacao de imoveis" in t:
        return "Aluguel de imóvel de pessoa física"
    if "locação" in t:
        return "Aluguel de bens de pessoa física"
    if "sent" in t and "judic" in t:
        return "Pagamento por decisão judicial"
    if "indeniz" in t or "vencimento" in t or "salár" in t:
        return "Servidor(a) (acerto ou indenização)"
    m = re.search(r"SERVI[ÇC]OS?\s+(?:PROFISSIONAIS\s+)?(?:DE|DA|DO|COMO)\s+([A-ZÇÃÕÁÉÍÓÚÂÊÔ ]{4,30}?)(?:\s+\d|\s+NO\b|\s+NA\b|\s+NAS\b|\s+NOS\b|\s+EM\b|\s+PARA\b|,|\.|$)", d)
    if m:
        return titulo(m.group(1).strip())
    return "Prestador(a) de serviço (pessoa física)"

def coletar(nome, ano, cache):
    tenant, ent = ENTIDADES[nome]
    empenhos = {e["id_empenho"]: e for e in todos("/lai/contabilidade/despesa/empenho", tenant, ent, ano)}
    brutos = todos("/lai/contabilidade/despesa/pagamento", tenant, ent, ano, 500)
    # o portal repete um mesmo pagamento em uma linha por documento bancário
    pagamentos = {(p["id_empenho"], p["nro_liquidacao"], p["numero_pagamento"]): p for p in brutos}.values()
    pagamentos = [p for p in pagamentos if p.get("tipo_empenho") == "Orçamentário" and p.get("id_empenho") in empenhos]

    # detalhe (descrição e licitação) das compras que vão aparecer e das pessoas físicas; fica em cache
    pago_emp = collections.defaultdict(float)
    for p in pagamentos:
        pago_emp[p["id_empenho"]] += p["valor_pago"] or 0
    def area_de(e):
        return FUNCOES.get((e.get("funcional_programatica") or "")[:2], "Outras áreas")
    por_area = collections.defaultdict(list)
    for i, e in empenhos.items():
        por_area["Câmara" if nome == "camara" else area_de(e)].append(e)
    precisa = set()
    for lista in por_area.values():
        pj = [e for e in lista if eh_compra(e, nome)]
        precisa |= {e["id_empenho"] for e in sorted(pj, key=lambda e: -(e.get("valor_empenho") or 0))[:TOP_COMPRAS]}
    precisa |= {i for i, e in empenhos.items() if eh_pessoa(e, nome)}
    chave = lambda i: f"{nome}:{ano}:{i}"
    faltam = [i for i in precisa if chave(i) not in cache]
    def busca(i):
        d = (chamar("/lai/contabilidade/despesa/detalhe/empenho", tenant, ent, ano, {"id_empenho": str(i)}).get("data") or [{}])[0]
        e = empenhos[i]
        if eh_pessoa(e, nome):
            r = normaliza_cargo(cargo(d.get("descricao_empenho"), d.get("descricao_despesa") or ""))
            if not pessoa_fisica(e.get("fornecedor_cpf_cnpj")) and r.startswith("Prestador"):
                t = conserta(d.get("descricao_despesa")).lower()
                tipo = ("obras" if "obra" in t else "móveis e equipamentos" if re.search(r"mobili|equipam|permanente", t)
                        else "materiais" if re.search(r"materia|consumo|aliment|combust", t) else "serviços")
                r = f"Microempreendedor(a) individual ({tipo})"
            return i, {"pf": r}   # só o cargo ou o serviço, nunca o nome
        lic = conserta(d.get("descricao_modalidade_licitacao") or "")
        return i, {"desc": conserta(d.get("descricao_empenho"))[:400], "acao": conserta(d.get("descricao_projetoatividade"))[:80],
                   "lic": re.sub(r":.*$", "", lic)[:60], "tipo": conserta(d.get("descricao_despesa"))[:60]}
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        for i, info in ex.map(busca, faltam):
            cache[chave(i)] = info
    print(f"  {nome}: {len(empenhos)} compras, {len(pagamentos)} pagamentos, {len(faltam)} detalhes novos")

    def rotulo(e):
        if eh_pessoa(e, nome):
            return (cache.get(chave(e["id_empenho"])) or {}).get("pf") or "Pessoa física", True
        n = conserta(e.get("fornecedor_nome")).strip()
        if n.lower() == "folha de pagamento" or (nome == "camara" and re.match(r"C[ÂA]MARA MUNICIPAL", n, re.I)):
            return ("Folha de pagamento (salários e subsídios, em bloco)" if nome == "camara" else "Folha de pagamento (salários, em bloco)"), False
        return n, False

    pagos_area = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0, False]))
    mes_area = collections.defaultdict(lambda: collections.defaultdict(float))
    ultima = ""
    for p in pagamentos:
        e = empenhos[p["id_empenho"]]
        a = "Câmara" if nome == "camara" else area_de(e)
        r, pf = rotulo(e)
        x = pagos_area[a][r]; x[0] += p["valor_pago"] or 0; x[1] += 1; x[2] = pf
        dd, mm, aa = p["data_pagamento"].split("/")
        mes_area[a][int(mm)] += p["valor_pago"] or 0
        ultima = max(ultima, f"{aa}-{mm}-{dd}")
    saida = {}
    for a, lista in por_area.items():
        receb = sorted(pagos_area[a].items(), key=lambda kv: -kv[1][0])
        compras = []
        pj = [e for e in lista if eh_compra(e, nome)]
        for e in sorted(pj, key=lambda e: -(e.get("valor_empenho") or 0))[:TOP_COMPRAS]:
            info = cache.get(chave(e["id_empenho"])) or {}
            r, _ = rotulo(e)
            pgs = sorted((p for p in pagamentos if p["id_empenho"] == e["id_empenho"]), key=lambda p: p["data_pagamento"][-4:] + p["data_pagamento"][3:5] + p["data_pagamento"][:2])
            compras.append({"n": f'{e.get("numero_empenho")}/{ano}', "data": e.get("data_empenho"), "quem": r,
                            "valor": round(e.get("valor_empenho") or 0, 2), "pago": round(pago_emp[e["id_empenho"]], 2),
                            "desc": info.get("desc", ""), "acao": info.get("acao", ""), "lic": info.get("lic", ""),
                            "unidade": titulo(conserta(e.get("descricao_unidade") or "")),
                            "pagamentos": [[p["data_pagamento"], round(p["valor_pago"] or 0, 2)] for p in pgs][:24]})
        total = sum(v[0] for _, v in receb)
        if not total and not compras:
            continue
        saida[a] = {"pago": round(total, 2), "por_mes": {str(k): round(v, 2) for k, v in sorted(mes_area[a].items())},
                    "recebedores": [{"nome": k, "pf": v[2], "valor": round(v[0], 2), "n": v[1]} for k, v in receb[:TOP_RECEB]],
                    "outros": round(sum(v[0] for _, v in receb[TOP_RECEB:]), 2), "n_outros": len(receb[TOP_RECEB:]),
                    "compras": compras}
    return {"areas": saida, "ultima": ultima, "portal": PORTAL[nome]}

def main(saida, arq_cache):
    ano = datetime.date.today().year
    cache = json.load(open(arq_cache, encoding="utf-8")) if os.path.exists(arq_cache) else {}
    dados = {"coletado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "ano": ano,
             "fonte": API}
    for nome in ENTIDADES:
        dados[nome] = coletar(nome, ano, cache)
    assert dados["prefeitura"]["areas"] and dados["camara"]["areas"], "portal sem dados"
    json.dump(cache, open(arq_cache, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    json.dump(dados, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("ok: pagamentos", ano, "| áreas da Prefeitura", len(dados["prefeitura"]["areas"]))

if __name__ == "__main__":
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception as e:
        if os.path.exists(sys.argv[1]):
            print(f"AVISO: pagamentos não atualizados ({e}). Mantida a última versão boa.")
        else:
            raise
