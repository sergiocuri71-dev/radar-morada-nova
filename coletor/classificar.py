"""Regra única para classificar o que cada vereador apresentou.
Ordem de checagem: homenagem > pergunta/cobrança > pedido de melhoria > outros.
Projetos de lei de autoria de vereador: homenagem (título, data comemorativa, nome de rua) ou proposta de lei."""
import re, unicodedata

def norm(t):
    t = unicodedata.normalize('NFD', t or '')
    return re.sub(r'\s+', ' ', ''.join(c for c in t if unicodedata.category(c) != 'Mn')).lower()

GRUPOS = {
  'melhoria':  'Pedidos de melhoria',
  'cobranca':  'Perguntas e cobranças',
  'homenagem': 'Homenagens',
  'lei':       'Propostas de lei',
  'outros':    'Outros',
}
EXPLICA = {
  'melhoria':  'Pede uma obra, um conserto ou um serviço: asfalto, iluminação, limpeza, quebra-molas, reforma, transporte, atendimento.',
  'cobranca':  'Pede informações, explicações ou providências sobre algo que já existe: quanto custou, quando fica pronto, por que não funciona.',
  'homenagem': 'Aplausos, parabéns, pesar, título de cidadão ou de honra ao mérito, nome de rua e criação de data comemorativa.',
  'lei':       'Projeto de lei, de lei complementar ou de resolução apresentado pelo vereador para criar ou mudar uma regra do município.',
  'outros':    'O que não se encaixa nos grupos acima.',
}
HOMENAGEM = r'(mocao de (aplauso|congratula|pesar|louvor|reconhecimento|parabens|homenagem)|voto de (pesar|aplauso|congratula|louvor)|aplausos|congratula|cidadao honorario|honra ao merito|homenage|denomina(cao|r|-se)?\b.*\b(rua|avenida|praca|via|logradouro|ponte|escola|unidade|predio|ginasio|estadio|quadra)|institui o dia|institui a semana|dia municipal|data comemorativa|falecimento)'
COBRANCA = r'(informa(cao|coes|r|e|ndo|do|da|dos|das)\b|previsao|resposta|enviado a esta casa|enviad[oa]s? a esta casa|planejamento|fila de espera|denuncia|esclarec|prestacao de contas|preste contas|quais (os|as|sao)|quantos|quantas|cronograma|relatorio|justifi(que|car) (o|a|os|as) (motivo|atraso)|motivo(s)? (do|da|pelo|pela|pelos|pelas)|por que|porque nao|copia (do|da|dos|das)|encaminhe(m)? (a|à)? ?esta casa)'
MELHORIA = r'(instala|manuten|constru|reforma|recupera|limpeza|capina|roçada|rocada|pavimenta|asfalt|calcament|cascalh|patrol|tapa-buraco|buraco|ilumina|lampad|poste|quebra-molas|redutor|faixa de pedestre|sinaliza|placa|manilha|bueiro|rede (de|pluvial|eletrica|de agua|de esgoto)|esgoto|agua|abastecimento|amplia|aquisi|compra|disponibiliz|contrata|implanta|cria(r|cao) de|transporte|onibus|veiculo|ambulancia|medic|consulta|exame|atendimento|academia|parque|praca|ponto de onibus|abrigo|cobertura|lixo|coleta|estrada|ponte|mata-burro|mata burro|plantio|arboriza|poda|desobstru|drenagem|meio-fio|meio fio|calcada|acessibilidade|rampa|camera|seguranca|vigilancia|internet|wi-?fi|sinal|telefon|curso|capacita|treinamento|programa|projeto|evento|festa|varri|pintura|tinta|vigia|guarda|reparo|conserto|substitui|troca)'

HOMENAGEM_PROP = r'(pesar|condolenc|falecimento|aplauso|congratula|parabeniz|louvor|homenagear|prestar homenagem|em homenagem a|reconhecimento (pelo|pela|aos|as|ao|a) )'

def classificar_proposicao(tipo, pedido_texto):
    """pedido_texto: o trecho do pedido (sem o cabeçalho). Decide pelo começo do pedido (primeiros 220 caracteres),
    que é onde fica o que está sendo pedido; a justificativa vem depois."""
    t = norm(pedido_texto)
    cabeca = t[:220]
    if 'mocao' in norm(tipo):
        return 'homenagem' if re.search(HOMENAGEM_PROP, t[:400]) else 'outros'
    if re.search(HOMENAGEM_PROP, cabeca):
        return 'homenagem'
    if re.search(COBRANCA, cabeca):
        return 'cobranca'
    if re.search(MELHORIA, cabeca):
        return 'melhoria'
    if re.search(MELHORIA, t):
        return 'melhoria'
    return 'outros'

def classificar_projeto(tipo, assunto):
    t = norm(assunto)
    if re.search(r'(cidadao honorario|honra ao merito|titulo de|institui o dia|institui a semana|dia municipal|denomina)', t):
        return 'homenagem'
    return 'lei'
