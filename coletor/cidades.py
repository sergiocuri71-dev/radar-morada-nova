"""Configuração de cada município acompanhado pelo Radar.
A cidade é escolhida pela variável de ambiente CIDADE (padrão: Morada Nova de Minas).
Morada Nova continua com os dados em dados/ e a página na raiz do site;
as outras ficam em dados/<slug>/ e _site/<slug>/."""
import os

CIDADES = {
    "morada-nova-de-minas": {
        "nome": "Morada Nova de Minas",
        "ibge": "3143500",
        "camara": "https://camaramoradanova.mg.gov.br",
        "cdn": 2433,
        "desde": None,  # coleta completa (histórico já existente)
        "intro": "Município da região central de Minas Gerais, às margens da represa de Três Marias.",
        "telefones_id": "1330857165",
        "balsas": "https://www.moradanova.mg.gov.br/detalhe-da-materia/info/atencao-confira-aqui-os-horarios-de-travessia-das-balsas-atualizados/46834",
        "tilapia": True,
        "pagamentos": True,
        "guia": "https://radarmnm.ironguia.com/",
        "vereadores": 9, "min_vereadores": 9, "min_props": 100, "min_projetos": 50,
    },
    "abaete": {
        "nome": "Abaeté",
        "ibge": "3100203",
        "camara": "https://camaraabaete.mg.gov.br",
        "cdn": 1979,
        "desde": 2025,  # só a legislatura atual, para não sobrecarregar o servidor da Câmara
        "intro": "Município da região central de Minas Gerais, vizinho à represa de Três Marias.",
        "tilapia": False,
        "vereadores": 9, "min_vereadores": 9, "min_props": 20, "min_projetos": 5,
    },
    "tres-marias": {
        "nome": "Três Marias",
        "ibge": "3169356",
        "camara": "https://cmtresmarias.mg.gov.br",
        "cdn": 2047,
        "desde": 2025,
        "intro": "Município da região central de Minas Gerais, onde fica a usina e a barragem da represa de Três Marias.",
        "tilapia": True,
        "vereadores": 11, "min_vereadores": 11, "min_props": 20, "min_projetos": 5,
    },
}
PADRAO = "morada-nova-de-minas"

def slug():
    return os.environ.get("CIDADE") or PADRAO

def atual():
    s = slug()
    if s not in CIDADES:
        raise SystemExit(f"cidade desconhecida: {s}")
    return dict(CIDADES[s], slug=s)

C = atual()
