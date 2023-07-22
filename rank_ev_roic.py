from datetime import datetime
import pandas as pd
import numpy as np
import json
from facade import conexao_pg

# Conexão com o PostgreSQL
conn = conexao_pg()

def rank_ev_roic():
    # Obtenção de dados
    query = "SELECT acao, ano, receita_liquida, custos, lucro_bruto,\
                    lucro_liquido, ebitda, ebit, imposto, divida_bruta, \
                    divida_liquida, margem_bruta, margem_ebitda, margem_liquida, \
                    roe, roic, patrimonio_liquido, payout, ev_ebit, \
                    liquidez_corrente, p_vp, lpa \
                    FROM public.acoes_contabil"

    query_ev = "SELECT ticker, cotacao, ev FROM public.acoes"

    df = pd.read_sql(query, conn)
    df_ev = pd.read_sql(query_ev, conn)

    df['ano'] = pd.to_datetime(df['ano'], format='%Y')
    ano_atual = datetime.now().year

    # Definir o número de anos a serem considerados
    num_years = 5

    # Obter a lista de ações únicas
    tickers = df['acao'].unique()

    # Criar DataFrame para armazenar classificações de empresas
    ranking_df = pd.DataFrame(columns=['acao', 'e_y', 'roic_score'])

    # Criar uma lista para armazenar os resultados intermediários
    intermediate_results = []

    # Treinar um modelo para cada ação
    for ticker in tickers:
        df_ticker = df[df['acao'] == ticker].copy()
        df_ticker.fillna(0, inplace=True)
        data_last_years = df_ticker[df_ticker['ano'].dt.year.isin(range(ano_atual - num_years, ano_atual + 1))]

        # Verificar se existem dados suficientes para os cálculos
        if len(data_last_years) > 0:
            # Obtém o valor EV para o ticker atual
            ev_value = df_ev[df_ev['ticker'] == ticker]['ev'].values[0]

            # Verificar se o valor de EV é diferente de zero
            if ev_value != 0:
                # Obtém os valores EBIT para os últimos 5 anos e calcula a média
                avg_ebit = data_last_years['ebit'].mean()
                # Calcula EY
                e_y = avg_ebit / ev_value * 100

                # Adiciona a classificação EY no DataFrame de classificação
                ranking_df = ranking_df._append({'acao': ticker, 'e_y': e_y}, ignore_index=True)

            # Computar a taxa média de crescimento do ROIC
            roic_values = data_last_years['roic'].values

            # Verificar se os valores do ROIC são diferentes de zero
            if len(roic_values) > 1 and any(roic_values != 0):
                # Apenas os pares onde o valor no denominador é diferente de zero
                nonzero_pairs = roic_values[:-1] != 0

                # Aplicar o filtro ao numerador e ao denominador
                numer = roic_values[1:][nonzero_pairs]
                denom = roic_values[:-1][nonzero_pairs]

                # Agora podemos calcular as taxas de crescimento sem o risco de divisão por zero
                growth_rates = (numer / denom) - 1
                avg_growth_rate = np.mean(growth_rates)

                # Média do ROIC
                avg_roic = np.mean(roic_values)

                # Define um score baseado no avg_roic e avg_growth_rate
                roic_score = avg_roic + avg_growth_rate

                # Adiciona a classificação ROIC no DataFrame de classificação
                ranking_df.loc[ranking_df['acao'] == ticker, 'roic_score'] = roic_score

        # Cria um dicionário para armazenar os resultados intermediários para este ticker
        ticker_results = {'ticker': ticker}

        # Adiciona os valores intermediários ao dicionário de resultados do ticker
        ticker_results['e_y'] = e_y
        ticker_results['roic_score'] = roic_score

        # Adiciona o dicionário de resultados do ticker à lista de resultados intermediários
        intermediate_results.append(ticker_results)

    # Ordenar as empresas com base na classificação EY e ROIC e atribuir um rank
    ranking_df['e_y_rank'] = ranking_df['e_y'].rank(ascending=False)
    ranking_df['roic_rank'] = ranking_df['roic_score'].rank(ascending=False)

    # Calcula o rank total somando o rank de EY e ROIC
    ranking_df['total_rank'] = ranking_df['e_y_rank'] + ranking_df['roic_rank']

    # Atualiza a tabela ações com a coluna rank
    for index, row in ranking_df.iterrows():
        update_query = f"UPDATE public.acoes SET rank = '{row['total_rank']}' WHERE ticker = '{row['acao']}'"
        cur = conn.cursor()
        cur.execute(update_query)
        conn.commit()

        # Adiciona os ranks ao dicionário de resultados intermediários correspondente
        for ticker_result in intermediate_results:
            if ticker_result['ticker'] == row['acao']:
                ticker_result['rank_e_y'] = row['e_y_rank']
                ticker_result['rank_roic'] = row['roic_rank']
                ticker_result['rank_total'] = row['total_rank']

    # Depois de todas as iterações, salve os resultados intermediários em um arquivo JSON
    with open('JSONS/intermediate_results.json', 'w') as f:
        json.dump(intermediate_results, f)
