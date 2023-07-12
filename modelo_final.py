from datetime import datetime

import numpy as np
import pandas as pd
from prophet import Prophet
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from facade import conexao_pg

# Conexão com o PostgreSQL
conn = conexao_pg()


def modelagem(target):
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

    # Inicializar um dicionário para armazenar os resultados
    results = {}

    avg_targets = None
    avg_targets_dv_liq_ebit = None
    avg_targets_dv_liq_patr_liq = None
    avg_growth_rate = None

    # Treinar um modelo para cada ação
    for ticker in tickers:
        df_ticker = df[df['acao'] == ticker].copy()
        df_ticker.fillna(0, inplace=True)
        data_last_years = df_ticker[df_ticker['ano'].dt.year.isin(range(ano_atual - num_years, ano_atual + 1))]

        if target == 'div_liq_ebit':
            data_last_years['div_liq_ebit'] = data_last_years['divida_liquida'] / data_last_years['ebit']
            growth_rates = (data_last_years['div_liq_ebit'].values[1:] / data_last_years['div_liq_ebit'].values[
                                                                         :-1]) - 1
            avg_targets_dv_liq_ebit = np.mean(growth_rates)

        elif target == 'div_liq_patr_liq':
            data_last_years['div_liq_patr_liq'] = data_last_years['divida_liquida'] / data_last_years[
                'patrimonio_liquido']
            growth_rates = (data_last_years['div_liq_patr_liq'].values[1:] / data_last_years['div_liq_patr_liq'].values[
                                                                             :-1]) - 1
            avg_targets_dv_liq_patr_liq = np.mean(growth_rates)

        elif target == 'e_y':
            # Obtém o valor EV para o ticker atual
            ev_value = df_ev[df_ev['ticker'] == ticker]['ev'].values[0]
            # Obtém os valores EBIT para os últimos 5 anos e calcula a média
            avg_ebit = data_last_years['ebit'].mean()
            # Calcula EY
            data_last_years['e_y'] = avg_ebit / ev_value * 100

            # Armazena a taxa de crescimento como NaN, uma vez que estamos calculando EY apenas para o ano mais recente
            growth_rates = np.nan

        else:
            # Computar a taxa média de crescimento
            growth_rates = (data_last_years[target].values[1:] / data_last_years[target].values[:-1]) - 1
            avg_growth_rate = np.mean(growth_rates)

            # Média do Targets
            avg_targets = np.mean(data_last_years[target].values)

        if target == 'roe' or target == 'roic' or target == 'margem_liquida':
            # Classificação baseada no valor médio do ROE e na taxa de crescimento
            if avg_targets > 0.15 and avg_growth_rate > 0:  # acima de 15% e crescendo
                category = 'SIM'
            elif avg_targets > 0.15 and avg_growth_rate <= 0:  # acima de 15% mas não crescendo
                category = 'ESTABILIDADE'
            else:  # abaixo de 15%
                category = 'NAO'

        elif target == 'liquidez_corrente':  # Adicione esta condição
            if avg_targets >= 1.5:  # Liquidez corrente é boa
                category = 'SIM'
            else:  # Liquidez corrente é ruim
                category = 'NAO'

        elif target == 'p_vp':  # Adicionada a condição para o P_VP
            if avg_targets <= 1.0:  # P/VP é bom
                category = 'SIM'
            else:  # P/VP é alto
                category = 'NAO'

        elif target == 'ev_ebit':  # Adicionada a condição para o P_VP
            if avg_targets < 10:  # se EV/EBIT for menor que 10
                category = 'SIM'
            else:  # se EV/EBIT for maior ou igual a 10
                category = 'NAO'

        elif target == 'div_liq_ebit':
            # Computar a taxa média da métrica
            if avg_targets_dv_liq_ebit <= 3:  # "Deve estar em no máximo 3x o EBIT."
                category = 'SIM'
            else:  # se a dívida líquida for mais de 3x o EBIT
                category = 'NAO'

        elif target == 'div_liq_patr_liq':
            # Computar a taxa média da métrica
            if avg_targets_dv_liq_patr_liq <= 1.5:  # "Deve estar no máximo 150% ou 1.5."
                category = 'SIM'
            else:  # se a dívida líquida for mais de 150% do patrimônio líquido
                category = 'NAO'

        elif target == 'e_y':
            # Computar a taxa média da métrica
            if data_last_years['e_y'].values[-1] >= 10:  # "Deve estar maior que 10% de retorno"
                category = 'SIM'
            else:  # se a dívida líquida for mais de 150% do patrimônio líquido
                category = 'NAO'

        else:
            # Classificar de acordo com a taxa média de crescimento
            if avg_growth_rate > 0.05:  # crescimento
                category = 'SIM'
            elif -0.05 <= avg_growth_rate <= 0.05:  # estabilidade
                category = 'ESTABILIDADE'
            else:  # queda
                category = 'NAO'

        # Prever o próximo ano se houver dados suficientes
        if data_last_years.shape[0] >= 3 and data_last_years[target].nunique() > 1:
            df_train = data_last_years[data_last_years['ano'].dt.year < ano_atual]
            df_test = data_last_years[data_last_years['ano'].dt.year == ano_atual - 1]

            if df_test.shape[0] > 0:
                model_exp_smoothing = ExponentialSmoothing(df_train[target])
                model_exp_smoothing = model_exp_smoothing.fit()

                model_prophet = Prophet()
                model_prophet.fit(df_train.rename(columns={'ano': 'ds', target: 'y'}))

                # Fazendo previsões
                exp_smoothing_pred = model_exp_smoothing.predict(start=len(df_train), end=len(df_train))
                prophet_pred = model_prophet.predict(df_test.rename(columns={'ano': 'ds'}))['yhat'].values

                exp_smoothing_pred = exp_smoothing_pred.values.flatten()

                # Combinação de modelos
                meta_train_features = np.array(
                    [model_exp_smoothing.predict(start=0, end=len(df_train) - 1).values.flatten(),
                     model_prophet.predict(df_train.rename(columns={'ano': 'ds'}))[
                         'yhat'].values.flatten()]).T

                # Verificando se temos algum valor NaN
                meta_train_features = np.nan_to_num(meta_train_features)

                model_meta = LinearRegression().fit(meta_train_features, df_train[target])

                # Agora podemos usar o modelo_meta para prever os valores do conjunto de teste
                meta_test_features = np.array([exp_smoothing_pred.flatten(), prophet_pred.flatten()]).T
                meta_prediction = model_meta.predict(meta_test_features)

                # Adicionar a previsão à categoria
                prediction = f' {category} - previsão: {meta_prediction[0]:.2f}'
                # category += prediction

                # Verificar e inserir ou atualizar a previsão na tabela "motivos_aportes"
                upsert_query = f"""
                INSERT INTO public.motivos_aportes (acao, data, modelo_motivo, target) 
                VALUES ('{ticker}', NOW(), '{prediction}', '{target}') 
                ON CONFLICT (acao, data, target) DO UPDATE SET modelo_motivo = '{prediction}';
                """
                cur = conn.cursor()
                cur.execute(upsert_query)
                conn.commit()
        elif target == 'e_y':
            meta_prediction = data_last_years['e_y'].values[-1]
            # Adicionar a previsão à categoria
            prediction = f' {category} - previsão: {meta_prediction:.2f}'
            # category += prediction

            # Verificar e inserir ou atualizar a previsão na tabela "motivos_aportes"
            upsert_query = f"""
                            INSERT INTO public.motivos_aportes (acao, data, modelo_motivo, target) 
                            VALUES ('{ticker}', NOW(), '{prediction}', '{target}') 
                            ON CONFLICT (acao, data, target) DO UPDATE SET modelo_motivo = '{prediction}';
                            """
            cur = conn.cursor()
            cur.execute(upsert_query)
            conn.commit()

        # Armazenar o resultado
        if target == 'div_liq_ebit':
            results[ticker] = {
                'modelo': category,
                'taxa_media_crescimento': avg_targets_dv_liq_ebit
            }
        elif target == 'div_liq_patr_liq':
            results[ticker] = {
                'modelo': category,
                'taxa_media_crescimento': avg_targets_dv_liq_patr_liq
            }
        elif target == 'e_y':
            results[ticker] = {
                'modelo': category,
                'taxa_media_crescimento': data_last_years['e_y'].values[-1]
            }
        else:
            results[ticker] = {
                'modelo': category,
                'taxa_media_crescimento': avg_growth_rate
            }

    # Inserir os resultados na tabela "acoes"
    for ticker, result in results.items():
        insert_query = f"UPDATE public.acoes SET {target} = '{result['modelo']}' WHERE ticker = '{ticker}'"
        cur = conn.cursor()
        cur.execute(insert_query)
        conn.commit()
