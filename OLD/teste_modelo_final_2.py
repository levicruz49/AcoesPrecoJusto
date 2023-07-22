import psycopg2
import pandas as pd
import json
import numpy as np
from sklearn.metrics import mean_absolute_error
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from prophet import Prophet
from scipy.stats import linregress

from facade import conexao_pg

# Conexão com o PostgreSQL
conn = conexao_pg()

# Obtenção de dados
query = "SELECT acao, ano, receita_liquida, lucro_liquido, ebitda, ebit, margem_liquida, roe, patrimonio_liquido, payout FROM public.acoes_contabil"
df = pd.read_sql(query, conn)
df['ano'] = pd.to_datetime(df['ano'], format='%Y')

tickers = df['acao'].unique()
results = {}

tscv = TimeSeriesSplit(n_splits=5)

for ticker in tickers:
    df_ticker = df[df['acao'] == ticker]

    if df_ticker.shape[0] <= 3 or df_ticker['receita_liquida'].nunique() <= 1:
        continue

    maes = []  # Armazenar o Mean Absolute Error de cada split
    for train_index, test_index in tscv.split(df_ticker):
        df_train, df_test = df_ticker.iloc[train_index], df_ticker.iloc[test_index]

        slope, _, _, _, _ = linregress(df_train.index.values, df_train['receita_liquida'])
        trend = 'SIM' if slope > 0 else 'NAO'

        # Modelos adicionados
        model_rf = RandomForestRegressor()
        model_rf.fit(df_train.index.values.reshape(-1, 1), df_train['receita_liquida'])

        model_gb = GradientBoostingRegressor()
        model_gb.fit(df_train.index.values.reshape(-1, 1), df_train['receita_liquida'])

        model_sarima = SARIMAX(df_train['receita_liquida'], order=(1, 1, 1))
        model_sarima = model_sarima.fit(disp=False)

        model_exp_smoothing = ExponentialSmoothing(df_train['receita_liquida'])
        model_exp_smoothing = model_exp_smoothing.fit()

        model_prophet = Prophet()
        model_prophet.fit(df_train.rename(columns={'ano': 'ds', 'receita_liquida': 'y'}))

        # Fazendo previsões
        rf_pred = model_rf.predict(df_test.index.values.reshape(-1, 1))
        gb_pred = model_gb.predict(df_test.index.values.reshape(-1, 1))
        sarima_pred = model_sarima.get_forecast(steps=df_test.shape[0]).predicted_mean
        exp_smoothing_pred = model_exp_smoothing.predict(start=df_test.index[0], end=df_test.index[-1])
        prophet_pred = model_prophet.predict(df_test.rename(columns={'ano': 'ds'}))['yhat'].values

        # Calculando a média das previsões para cada ponto no df_test
        avg_predictions = np.mean(np.array([rf_pred, gb_pred, sarima_pred, exp_smoothing_pred, prophet_pred]), axis=0)

        # Computando o erro
        mae = mean_absolute_error(df_test["receita_liquida"], avg_predictions)
        maes.append(mae)

    # Use a média dos erros para ajustar seus modelos, se necessário
    avg_mae = np.mean(maes)
    # print(f'Average MAE for {ticker}: {avg_mae}')

    if not df_test.empty:
        results[ticker] = {
            'valor_real_2022': df_test["receita_liquida"].values[0],
            'Average MAE for': avg_mae,
            'avg_predicao_2022': list(avg_predictions),  # Convert numpy array to list
            'tendencia': trend
        }

# Salvar os resultados como um arquivo json
with open('../JSONS/results.json', 'w') as f:
    json.dump(results, f)
