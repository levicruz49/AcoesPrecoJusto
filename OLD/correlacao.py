import pandas as pd

from facade import conexao_pg

# Conexão com o PostgreSQL
conn = conexao_pg()

# Leitura dos dados da tabela "acoes_contabil"
query_acoes_contabil = """
SELECT ano, receita_liquida, custos, lucro_bruto, lucro_liquido, ebitda, ebit, \
            imposto, divida_bruta, divida_liquida, margem_bruta, margem_ebitda, margem_liquida, \
            roe, roic, patrimonio_liquido, payout, ev_ebit, liquidez_corrente, p_vp, lpa
FROM public.acoes_contabil
"""

df = pd.read_sql(query_acoes_contabil, conn)
df = df.fillna(0)

# Calcular a matriz de correlação
corr_matrix = df.corr()

# Transformar a matriz de correlação em um DataFrame "melted" para facilitar a leitura
correlations_df = corr_matrix.unstack().reset_index()
correlations_df.columns = ['var1', 'var2', 'correlation']

# Remove self-correlations
correlations_df = correlations_df[correlations_df['var1'] != correlations_df['var2']]

# Considerar apenas correlações fortes
correlations_df = correlations_df[(correlations_df['correlation'] > 0.7) | (correlations_df['correlation'] < -0.7)]

print(correlations_df)

conn.close()
