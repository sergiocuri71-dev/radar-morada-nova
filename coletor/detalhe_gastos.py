"""Detalhe dos gastos por área (função), setor (subfunção) e tipo de despesa (elemento),
a partir da Matriz de Saldos Contábeis (MSC) que o município envia todo mês ao Tesouro (Siconfi).
Valores liquidados acumulados no ano, sem as operações entre órgãos do próprio município
(intra-orçamentárias), para bater com o relatório bimestral (RREO)."""
import collections

FUNCOES = {"01": "Legislativa", "02": "Judiciária", "03": "Essencial à Justiça", "04": "Administração",
    "05": "Defesa Nacional", "06": "Segurança Pública", "07": "Relações Exteriores", "08": "Assistência Social",
    "09": "Previdência Social", "10": "Saúde", "11": "Trabalho", "12": "Educação", "13": "Cultura",
    "14": "Direitos da Cidadania", "15": "Urbanismo", "16": "Habitação", "17": "Saneamento", "18": "Gestão Ambiental",
    "19": "Ciência e Tecnologia", "20": "Agricultura", "21": "Organização Agrária", "22": "Indústria",
    "23": "Comércio e Serviços", "24": "Comunicações", "25": "Energia", "26": "Transporte", "27": "Desporto e Lazer",
    "28": "Encargos Especiais", "99": "Reserva de Contingência"}

# Portaria MOG nº 42/1999 (subfunções)
SUBFUNCOES = {"031": "Ação legislativa", "032": "Controle externo", "061": "Ação judiciária",
    "062": "Defesa do interesse público no processo judiciário", "091": "Defesa da ordem jurídica",
    "092": "Representação judicial e extrajudicial", "121": "Planejamento e orçamento", "122": "Administração geral",
    "123": "Administração financeira", "124": "Controle interno", "125": "Normatização e fiscalização",
    "126": "Tecnologia da informação", "127": "Ordenamento territorial", "128": "Formação de recursos humanos",
    "129": "Administração de receitas", "130": "Administração de concessões", "131": "Comunicação social",
    "181": "Policiamento", "182": "Defesa civil", "183": "Informação e inteligência",
    "241": "Assistência ao idoso", "242": "Assistência ao portador de deficiência",
    "243": "Assistência à criança e ao adolescente", "244": "Assistência comunitária",
    "245": "Serviços socioassistenciais", "271": "Previdência básica", "272": "Previdência do regime estatutário",
    "273": "Previdência complementar", "274": "Previdência especial", "301": "Atenção básica",
    "302": "Assistência hospitalar e ambulatorial", "303": "Suporte profilático e terapêutico",
    "304": "Vigilância sanitária", "305": "Vigilância epidemiológica", "306": "Alimentação e nutrição",
    "331": "Proteção e benefícios ao trabalhador", "332": "Relações de trabalho", "333": "Empregabilidade",
    "334": "Fomento ao trabalho", "361": "Ensino fundamental", "362": "Ensino médio", "363": "Ensino profissional",
    "364": "Ensino superior", "365": "Educação infantil", "366": "Educação de jovens e adultos",
    "367": "Educação especial", "368": "Educação básica", "391": "Patrimônio histórico, artístico e arqueológico",
    "392": "Difusão cultural", "421": "Custódia e reintegração social", "422": "Direitos individuais, coletivos e difusos",
    "423": "Assistência aos povos indígenas", "451": "Infraestrutura urbana", "452": "Serviços urbanos",
    "453": "Transportes coletivos urbanos", "481": "Habitação rural", "482": "Habitação urbana",
    "511": "Saneamento básico rural", "512": "Saneamento básico urbano", "541": "Preservação e conservação ambiental",
    "542": "Controle ambiental", "543": "Recuperação de áreas degradadas", "544": "Recursos hídricos",
    "545": "Meteorologia", "571": "Desenvolvimento científico", "572": "Desenvolvimento tecnológico e engenharia",
    "573": "Difusão do conhecimento científico e tecnológico", "601": "Promoção da produção vegetal",
    "602": "Promoção da produção animal", "603": "Defesa sanitária vegetal", "604": "Defesa sanitária animal",
    "605": "Abastecimento", "606": "Extensão rural", "607": "Irrigação", "631": "Reforma agrária",
    "632": "Colonização", "661": "Promoção industrial", "662": "Produção industrial", "663": "Mineração",
    "664": "Propriedade industrial", "665": "Normalização e qualidade", "691": "Promoção comercial",
    "692": "Comercialização", "693": "Comércio exterior", "694": "Serviços financeiros", "695": "Turismo",
    "721": "Comunicações postais", "722": "Telecomunicações", "751": "Conservação de energia",
    "752": "Energia elétrica", "753": "Combustíveis minerais", "754": "Biocombustíveis",
    "781": "Transporte aéreo", "782": "Transporte rodoviário", "783": "Transporte ferroviário",
    "784": "Transporte hidroviário", "785": "Transportes especiais", "811": "Desporto de rendimento",
    "812": "Desporto comunitário", "813": "Lazer", "841": "Refinanciamento da dívida interna",
    "842": "Refinanciamento da dívida externa", "843": "Serviço da dívida interna", "844": "Serviço da dívida externa",
    "845": "Outras transferências", "846": "Outros encargos especiais", "847": "Transferências para a educação básica",
    "999": "Reserva de contingência"}

# Elementos de despesa (Portaria Interministerial nº 163/2001), em linguagem simples
ELEMENTOS = {"01": "Aposentadorias e reformas", "03": "Pensões", "04": "Contratos temporários (pessoal)",
    "05": "Outros benefícios previdenciários", "07": "Contribuição a previdência complementar",
    "08": "Benefícios assistenciais (auxílios a servidores e famílias)", "11": "Salários e subsídios (servidores e agentes políticos)",
    "13": "Encargos sobre a folha (INSS, previdência)", "14": "Diárias de viagem", "16": "Horas extras e outras despesas variáveis de pessoal",
    "18": "Bolsas de estudo", "20": "Bolsas de estudo no exterior", "21": "Juros da dívida", "22": "Encargos da dívida",
    "30": "Material de consumo (combustível, alimentos, remédios, escritório…)", "31": "Premiações",
    "32": "Material para distribuição gratuita", "33": "Passagens e transporte", "34": "Terceirização de mão de obra (pessoal)",
    "35": "Consultoria", "36": "Serviços de pessoas físicas", "37": "Locação de mão de obra",
    "39": "Serviços de empresas (manutenção, transporte, eventos…)", "40": "Serviços de informática e telefonia",
    "41": "Contribuições", "42": "Auxílios", "43": "Subvenções sociais", "45": "Subvenções econômicas",
    "46": "Auxílio-alimentação", "47": "Impostos e taxas pagos", "48": "Auxílio financeiro a pessoas físicas",
    "49": "Auxílio-transporte", "51": "Obras e instalações", "52": "Equipamentos e material permanente",
    "61": "Compra de imóveis", "65": "Participação em empresas", "71": "Pagamento da dívida (principal)",
    "81": "Repasses constitucionais", "91": "Sentenças judiciais", "92": "Despesas de anos anteriores",
    "93": "Indenizações e restituições", "94": "Indenizações trabalhistas", "96": "Ressarcimento de pessoal cedido",
    "97": "Aporte para a previdência dos servidores", "99": "A classificar"}
MODALIDADE = {"30": " (repasse ao Estado)", "50": " (a entidades sem fins lucrativos)",
              "70": " (a consórcios públicos)", "71": " (a consórcios públicos)"}
PODERES = {"10131": "prefeitura", "20231": "camara", "10132": "previdencia"}
LIQUIDADO = ("622130300", "622130400")   # crédito liquidado a pagar + liquidado pago

def tipo_gasto(nat):
    if not nat or nat.startswith("99"):
        return "Reserva de contingência"
    mod, el = nat[2:4], nat[4:6]
    if mod in ("71", "70") and el == "00":
        return "Rateio de consórcios públicos (saúde, obras…)"
    return ELEMENTOS.get(el, f"Elemento {el}") + MODALIDADE.get(mod, "")

def montar(itens):
    """itens: linhas da MSC (classe 6, ending_balance). Devolve o detalhe por poder e por área."""
    soma = lambda: collections.defaultdict(float)
    area_sub, area_tipo, area_tot = collections.defaultdict(soma), collections.defaultdict(soma), soma()
    poder_tipo, poder_tot = collections.defaultdict(soma), soma()
    pago_area, pago_poder = soma(), soma()   # tudo o que saiu do caixa (com os repasses internos), para comparar com os portais
    for x in itens:
        if x["conta_contabil"] == "622130400" and x.get("natureza_despesa"):
            v = x["valor"] if x["natureza_conta"] == "C" else -x["valor"]
            pago_area[x.get("funcao") or "??"] += v
            pago_poder[PODERES.get(x.get("poder_orgao"), "outros")] += v
    for x in itens:
        nat = x.get("natureza_despesa") or ""
        if x["conta_contabil"] not in LIQUIDADO or not nat or nat[2:4] == "91":
            continue
        v = x["valor"] if x["natureza_conta"] == "C" else -x["valor"]
        f = x.get("funcao") or "??"
        t = tipo_gasto(nat)
        area_sub[f][SUBFUNCOES.get(x.get("subfuncao") or "", "Outros")] += v
        area_tipo[f][t] += v
        area_tot[f] += v
        p = PODERES.get(x.get("poder_orgao"), "outros")
        poder_tipo[p][t] += v
        poder_tot[p] += v
    lista = lambda d: [{"nome": k, "valor": round(v, 2)} for k, v in sorted(d.items(), key=lambda kv: -kv[1]) if round(v, 2) > 0]
    areas = {FUNCOES.get(f, f): {"total": round(area_tot[f], 2), "pago_tesouro": round(pago_area[f], 2), "setores": lista(area_sub[f]), "tipos": lista(area_tipo[f])}
             for f in area_tot if area_tot[f] > 0}
    poderes = {p: {"total": round(poder_tot[p], 2), "pago_tesouro": round(pago_poder[p], 2), "tipos": lista(poder_tipo[p])} for p in poder_tot if poder_tot[p] > 0}
    return {"areas": areas, "poderes": poderes}
