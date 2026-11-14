# Radar da Câmara de Morada Nova de Minas

O que cada vereador de Morada Nova de Minas (MG) faz — propostas, votos e presença — e as contas da Prefeitura e da Câmara,
só com dados oficiais: o site da Câmara Municipal (https://camaramoradanova.mg.gov.br) e os relatórios fiscais que o município
entrega ao Tesouro Nacional (Siconfi).

Projeto independente, sem ligação com a Câmara ou com partidos. O site não dá nota nem opinião.

## Como funciona
Todo dia de madrugada, um robô (GitHub Actions, arquivo `.github/workflows/atualizar.yml`):

1. coleta os dados no site da Câmara (`coletor/coletar.py`), devagar, para não pesar no servidor;
2. confere se a coleta veio completa (`coletor/verificar.py`). Se vier incompleta ou estranha, **não publica** e o site fica com a última versão boa;
3. coleta receitas e despesas no Tesouro Nacional (`coletor/financas.py`): relatório bimestral do ano corrente, balanço anual do ano anterior e gasto com pessoal da Prefeitura e da Câmara;
4. coleta números da cidade no IBGE (população, área, PIB, produção de tilápia, distritos) e os telefones úteis publicados pela Câmara (`coletor/cidade.py`);
5. lê as atas das reuniões, que são PDFs escaneados, com OCR (`coletor/atas.py`), para registrar ausências;
6. monta a página (`coletor/montar.py` + `coletor/modelo.html`) e publica no GitHub Pages.

Os dados de cada dia ficam guardados na pasta `dados/`, com histórico.

## Regras
- Só dado oficial. Cada número tem link para a página da Câmara de onde saiu.
- Mesma régua para todos os vereadores (classificação em `coletor/classificar.py`, lugares e temas em `coletor/lugares.py`).
- O que é estimativa ou leitura automática está escrito ao lado do número.
- Dado ausente não é falta.

## Achou um erro?
Abra uma *issue* neste repositório.
