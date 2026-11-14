"""Confere se a coleta nova está completa antes de publicar.
Compara com a última versão boa (a que está no repositório). Se algo parecer estranho, sai com erro
e o robô não publica: o site continua com a última versão boa.
Uso: python3 verificar.py dados/data.json novo/data.json"""
import json, sys

antigo = json.load(open(sys.argv[1], encoding="utf-8")) if len(sys.argv) > 2 else None
novo = json.load(open(sys.argv[-1], encoding="utf-8"))
erros = []
n = {k: len(novo.get(k, [])) for k in ("vereadores", "proposicoes", "votacoes", "projetos")}
print("coleta nova:", n)
if n["vereadores"] != 9:
    erros.append(f"esperava 9 vereadores, vieram {n['vereadores']}")
for v in novo["vereadores"]:
    if not v.get("partido") or "estatisticas" not in v:
        erros.append(f"vereador sem partido ou estatísticas: {v.get('nome')}")
if antigo:
    a = {k: len(antigo.get(k, [])) for k in n}
    print("última versão boa:", a)
    for k in ("proposicoes", "votacoes", "projetos"):
        if n[k] < a[k] * 0.95:
            erros.append(f"{k} caiu de {a[k]} para {n[k]}")
sem_texto = sum(1 for p in novo["proposicoes"] if not (p.get("texto_completo") or "").strip())
if sem_texto > 5:
    erros.append(f"{sem_texto} proposições sem texto")
if erros:
    print("COLETA SUSPEITA, não publicar:")
    for e in erros:
        print(" -", e)
    sys.exit(1)
print("ok: coleta conferida")
