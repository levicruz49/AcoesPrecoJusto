import psycopg2
import pandas as pd
import json
from sklearn.metrics import mean_absolute_error
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from prophet import Prophet
import numpy as np
from scipy.stats import linregress
from keras.models import Sequential
from keras.layers import LSTM, Dense

from facade import conexao_pg

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

    n_features = 1
    n_steps = len(df_train.index.values)
    X, y = df_train.index.values.reshape((n_steps, 1, n_features)), df_train['receita_liquida']

    model_lstm = Sequential()
    model_lstm.add(LSTM(50, activation='relu', input_shape=(1, n_features)))
    model_lstm.add(Dense(1))
    model_lstm.compile(optimizer='adam', loss='mse')

    model_lstm.fit(X, y, epochs=200, verbose=0)

    # Fazendo previsões
    rf_pred = model_rf.predict(df_test.index.values.reshape(-1, 1))
    gb_pred = model_gb.predict(df_test.index.values.reshape(-1, 1))
    sarima_pred = model_sarima.get_forecast(steps=df_test.shape[0]).predicted_mean
    exp_smoothing_pred = model_exp_smoothing.predict(start=df_test.index[0], end=df_test.index[-1])
    prophet_pred = model_prophet.predict(df_test.rename(columns={'ano': 'ds'}))['yhat'].values
    lstm_pred = model_lstm.predict(df_test.index.values.reshape(-1, 1, n_features))

    # Calculando a média das previsões
    predictions = np.array([rf_pred[0], gb_pred[0], sarima_pred.iloc[-1] if not sarima_pred.empty else np.nan,
                            exp_smoothing_pred.iloc[-1] if not exp_smoothing_pred.empty else np.nan,
                            prophet_pred[0], lstm_pred[0][0]])

    avg_prediction = np.nanmean(predictions)

    results[ticker] = {
        'valor_real_2022': df_test["receita_liquida"].values[0],
        'avg_predicao_2022': avg_prediction,
        'tendencia': trend
    }

# Salvar os resultados como um arquivo json
with open('../JSONS/results.json', 'w') as f:
    json.dump(results, f)