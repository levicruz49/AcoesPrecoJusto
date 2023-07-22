from datetime import datetime

import numpy as np
import optuna
import pandas as pd
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from facade import conexao_pg, insere_previsao_e_motivo_tb_motivos_aportes

# Conexão com o PostgreSQL
conn = conexao_pg()

cv_results = {}

# Obtenção de dados
query = "SELECT acao, ano, receita_liquida, custos, lucro_bruto,\
                        lucro_liquido, ebitda, ebit, imposto, divida_bruta, \
                        divida_liquida, margem_bruta, margem_ebitda, margem_liquida, \
                        roe, roic, patrimonio_liquido, payout, ev_ebit, \
                        liquidez_corrente, p_vp, lpa \
                        FROM public.acoes_contabil"

query_ev = "SELECT ticker, cotacao, ev FROM public.acoes"

query_feitos = f"SELECT acao, data, target FROM public.motivos_aportes WHERE data = '{datetime.now().date()}'"


def objective_factory(df_train, target):
    def objective(trial):
        params = {
            'seasonality_mode': trial.suggest_categorical('seasonality_mode', ['additive', 'multiplicative']),
            'changepoint_prior_scale': trial.suggest_loguniform('changepoint_prior_scale', 0.001, 0.5),
            'seasonality_prior_scale': trial.suggest_loguniform('seasonality_prior_scale', 0.01, 10),
        }

        model_prophet = Prophet(**params)
        model_prophet.fit(df_train.rename(columns={'ano': 'ds', target: 'y'}))

        try:
            df_cv = cross_validation(model_prophet, initial='1095 days', period='3 days', horizon='365 days')
        except:
            df_cv = cross_validation(model_prophet, initial='730 days', period='2 days', horizon='365 days')

        try:
            df_p = performance_metrics(df_cv, rolling_window=1)
        except:
            df_p = performance_metrics(df_cv, rolling_window=1)
        return df_p['mape'].values[0]

    return objective


def modelagem(target):
    df = pd.read_sql(query, conn)

    df['ano'] = pd.to_datetime(df['ano'], format='%Y')
    ano_atual = datetime.now().year

    # Definir o número de anos a serem considerados
    num_years = 5

    # Obter a lista de ações únicas
    tickers = df['acao'].unique()


    # Treinar um modelo para cada ação
    for ticker in tickers:

        df_ticker = df[df['acao'] == ticker].copy()
        df_ticker.fillna(0, inplace=True)

        data_last_years = df_ticker[df_ticker['ano'].dt.year.isin(range(ano_atual - num_years, ano_atual + 1))]
        years_available = df_ticker['ano'].dt.year.max() - df_ticker['ano'].dt.year.min()

        if years_available <= 2:
            continue

        # Prever o próximo ano se houver dados suficientes
        if data_last_years.shape[0] >= 3 and data_last_years[target].nunique() > 1:
            df_train = data_last_years[data_last_years['ano'].dt.year < ano_atual]
            df_test = data_last_years[data_last_years['ano'].dt.year == ano_atual - 1]

            if df_test.shape[0] > 0:
                model_exp_smoothing = ExponentialSmoothing(df_train[target])
                model_exp_smoothing = model_exp_smoothing.fit(smoothing_level=0.2, optimized=False)

                study = optuna.create_study(direction='minimize')
                # study.optimize(objective_factory(df_train, target), n_trials=50, n_jobs=-1)
                study.optimize(objective_factory(df_train, target), n_trials=25, n_jobs=-1)

                model_prophet = Prophet(**study.best_params)
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
                try:
                    df_cv = cross_validation(model_prophet, initial='1095 days', period='365 days', horizon='365 days')
                except:
                    df_cv = cross_validation(model_prophet, initial='730 days', period='365 days', horizon='365 days')

                df_p = performance_metrics(df_cv, rolling_window=1)
                cv_results[ticker] = df_p

                # Adicionar a previsão à categoria
                prediction = f'previsão: {meta_prediction[0]:.2f}'
                # category += prediction

                # Verificar e inserir ou atualizar a previsão na tabela "motivos_aportes"
                insere_previsao_e_motivo_tb_motivos_aportes(ticker, prediction, target)
