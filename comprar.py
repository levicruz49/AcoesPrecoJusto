import pandas as pd
import numpy as np
from facade import conexao_pg

# Conexão com o PostgreSQL
conn = conexao_pg()

# Leitura dos dados da tabela "acoes"
query_acoes = """
SELECT ticker, cotacao, preco_justo_bazin, receita_liquida, lucro_liquido, roic, 
       margem_liquida, div_liq_ebit, ev_ebit, div_liq_patr_liq, roe, liquidez_corrente, 
       p_vp, e_y, comprar, rank
FROM public.acoes
"""
df_acoes = pd.read_sql(query_acoes, conn)

# Implementação das regras para a coluna "comprar"
def regras(row):
    # Regra do preço justo
    if row['preco_justo_bazin'] > row['cotacao']:
        preco_justo = 'SIM'
    else:
        preco_justo = 'NAO'

    # Regra para as outras colunas
    outras_colunas = row['receita_liquida':'rank'].tolist()
    num_sim = outras_colunas.count('SIM')
    num_estabilidade = outras_colunas.count('ESTABILIDADE')
    num_nao = outras_colunas.count('NAO')
    if num_sim + num_estabilidade > num_nao:
        outras = 'SIM'
    else:
        outras = 'NAO'

    # Decisão final
    if preco_justo == 'SIM' and outras == 'SIM':
        return 'SIM'
    else:
        return 'NAO'

df_acoes['comprar'] = df_acoes.apply(regras, axis=1)

# Atualização da tabela no banco de dados
for index, row in df_acoes.iterrows():
    update_query = f"""
    UPDATE public.acoes SET comprar = '{row['comprar']}' WHERE ticker = '{row['ticker']}'
    """
    cur = conn.cursor()
    cur.execute(update_query)
    conn.commit()

conn.close()
