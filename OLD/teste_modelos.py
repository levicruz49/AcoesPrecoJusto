import psycopg2
import pandas as pd
import json
from sklearn.metrics import mean_squared_error
from math import sqrt
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from prophet import Prophet

from facade import conexao_pg


def format_value(val):
    return "{:,.0f}".format(val)  # Formate os valores como strings com separadores de milhares


# Conexão com o PostgreSQL
conn = conexao_pg()

# Obtenção de dados
query = "SELECT acao, ano, receita_liquida, lucro_liquido, ebitda, ebit, margem_liquida, roe, patrimonio_liquido, payout FROM public.acoes_contabil"
df = pd.read_sql(query, conn)
df['ano'] = pd.to_datetime(df['ano'], format='%Y')

tickers = df['acao'].unique()
results = {}

for ticker in tickers:
    df_ticker = df[df['acao'] == ticker]

    if df_ticker.shape[0] <= 3 or df_ticker['receita_liquida'].nunique() <= 1:
        continue

    df_train = df_ticker[df_ticker['ano'].dt.year < 2022]
    df_test = df_ticker[df_ticker['ano'].dt.year == 2022]

    if df_test.shape[0] == 0:
        continue

    model_sarima = SARIMAX(df_train['receita_liquida'], order=(1, 1, 1))
    model_sarima = model_sarima.fit(disp=False)

    model_exp_smoothing = ExponentialSmoothing(df_train['receita_liquida'])
    model_exp_smoothing = model_exp_smoothing.fit()

    model_prophet = Prophet()
    model_prophet.fit(df_train.rename(columns={'ano': 'ds', 'receita_liquida': 'y'}))

    sarima_pred = model_sarima.predict(start=df_test.index[0], end=df_test.index[-1])
    exp_smoothing_pred = model_exp_smoothing.predict(start=df_test.index[0], end=df_test.index[-1])
    prophet_pred = model_prophet.predict(df_test.rename(columns={'ano': 'ds'}))['yhat'].values

    sarima_rmse = sqrt(mean_squared_error(df_test['receita_liquida'], sarima_pred))
    exp_smoothing_rmse = sqrt(mean_squared_error(df_test['receita_liquida'], exp_smoothing_pred))
    prophet_rmse = sqrt(mean_squared_error(df_test['receita_liquida'], prophet_pred))

    future = model_prophet.make_future_dataframe(periods=2, freq='Y')
    forecast = model_prophet.predict(future)

    results[ticker] = {
        'valor_real_2022': format_value(df_test["receita_liquida"].values[0]),
        # 'sarima_rmse': format_value(sarima_rmse),
        'sarima_predicao_2022': format_value(sarima_pred.values[-1]),
        # 'exp_smoothing_rmse': format_value(exp_smoothing_rmse),
        'exp_smoothing_predicao_2022': format_value(exp_smoothing_pred.values[-1]),
        # 'prophet_rmse': format_value(prophet_rmse),
        'prophet_predicao_2022': format_value(prophet_pred[-1]),
        'prophet_predicao_2023': format_value(forecast["yhat"].values[-2]),
        'prophet_predicao_2024': format_value(forecast["yhat"].values[-1]),
    }

# Escreva os resultados em um arquivo JSON
with open('../JSONS/previsoes.json', 'w') as fp:
    json.dump(results, fp)
