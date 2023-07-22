import numpy as np
import pandas as pd
import json
from sklearn.metrics import mean_absolute_error
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from prophet import Prophet
from keras.models import Sequential
from keras.layers import LSTM, Dense

from facade import conexao_pg


def check_ticker_in_file(ticker):
    # Verifica se o ticker já foi processado lendo o arquivo JSON
    with open('../JSONS/results.json', 'r') as f:
        results = json.load(f)

        if ticker in results:
            return True
        else:
            return False

# Conexão com o PostgreSQL
conn = conexao_pg()

# Obtenção de dados
query = "SELECT acao, ano, receita_liquida, lucro_liquido, ebitda, ebit, margem_liquida, roe, patrimonio_liquido, payout FROM public.acoes_contabil"
df = pd.read_sql(query, conn)
df['ano'] = pd.to_datetime(df['ano'], format='%Y')

tickers = df['acao'].unique()
results = {}

# Feature Engineering
features = ['lucro_liquido', 'ebitda', 'ebit', 'margem_liquida', 'roe', 'patrimonio_liquido', 'payout']

# Cross Validation
# Fazer split do treino/validação/teste de acordo com as suas necessidades

for ticker in tickers:

    if check_ticker_in_file(ticker):
        continue

    df_ticker = df[df['acao'] == ticker]

    if df_ticker.shape[0] <= 3 or df_ticker['receita_liquida'].nunique() <= 1:
        continue

    df_train = df_ticker[df_ticker['ano'].dt.year < 2022]
    df_test = df_ticker[df_ticker['ano'].dt.year == 2022]

    if df_test.shape[0] == 0:
        continue

    if df_train.shape[0] < 5:
        continue

    # Ajuste de hiperparâmetros
    param_grid = {'n_estimators': [50, 100, 200], 'max_depth': [None, 5, 10, 15], 'min_samples_split': [2, 5, 10]}
    n_splits = min(5, df_train.shape[0])
    model_rf = GridSearchCV(RandomForestRegressor(), param_grid, cv=n_splits)
    model_rf.fit(df_train[features], df_train['receita_liquida'])

    param_grid = {'n_estimators': [50, 100, 200], 'learning_rate': [0.1, 0.05, 0.01], 'max_depth': [3, 5, 10]}
    model_gb = GridSearchCV(GradientBoostingRegressor(), param_grid, cv=n_splits)
    model_gb.fit(df_train[features], df_train['receita_liquida'])

    model_sarima = SARIMAX(df_train['receita_liquida'], order=(1, 1, 1))
    model_sarima = model_sarima.fit(disp=False)

    model_exp_smoothing = ExponentialSmoothing(df_train['receita_liquida'])
    model_exp_smoothing = model_exp_smoothing.fit(smoothing_level=0.2, optimized=False)

    model_prophet = Prophet(seasonality_mode='multiplicative')
    model_prophet.fit(df_train.rename(columns={'ano': 'ds', 'receita_liquida': 'y'}))

    n_features = len(features)
    n_steps = len(df_train.index.values)
    X, y = df_train[features].values.reshape((n_steps, 1, n_features)), df_train['receita_liquida']

    model_lstm = Sequential()
    model_lstm.add(LSTM(50, activation='relu', input_shape=(1, n_features)))
    model_lstm.add(Dense(1))
    model_lstm.compile(optimizer='adam', loss='mse')

    model_lstm.fit(X, y, epochs=200, verbose=0)

    # Fazendo previsões com modelos treinados
    rf_pred_train = model_rf.predict(df_train[features])
    gb_pred_train = model_gb.predict(df_train[features])
    sarima_pred_train = model_sarima.predict(start=0, end=df_train.shape[0] - 1)
    exp_smoothing_pred_train = model_exp_smoothing.predict(start=0, end=df_train.shape[0] - 1)
    prophet_pred_train = model_prophet.predict(df_train.rename(columns={'ano': 'ds'}))['yhat'].values
    lstm_pred_train = model_lstm.predict(df_train[features].values.reshape(-1, 1, n_features))

    # Verificando se temos algum valor NaN
    lstm_pred_train = np.nan_to_num(lstm_pred_train)
    sarima_pred_train = sarima_pred_train.fillna(0)
    exp_smoothing_pred_train = exp_smoothing_pred_train.fillna(0)

    meta_features_train = np.column_stack((rf_pred_train, gb_pred_train, sarima_pred_train, exp_smoothing_pred_train,
                                           prophet_pred_train, lstm_pred_train))

    # Verificando se temos algum valor NaN
    meta_features_train = np.nan_to_num(meta_features_train)

    model_meta = LinearRegression().fit(meta_features_train, df_train["receita_liquida"])

    # Fazendo previsões no conjunto de teste
    rf_pred_test = model_rf.predict(df_test[features])
    gb_pred_test = model_gb.predict(df_test[features])
    sarima_pred_test = model_sarima.predict(start=df_train.shape[0], end=df_train.shape[0] + df_test.shape[0] - 1)
    exp_smoothing_pred_test = model_exp_smoothing.predict(start=df_train.shape[0],
                                                          end=df_train.shape[0] + df_test.shape[0] - 1)
    prophet_pred_test = model_prophet.predict(df_test.rename(columns={'ano': 'ds'}))['yhat'].values
    lstm_pred_test = model_lstm.predict(df_test[features].values.reshape(-1, 1, n_features))

    # Verificando se temos algum valor NaN
    lstm_pred_test = np.nan_to_num(lstm_pred_test)
    sarima_pred_test = sarima_pred_test.fillna(0)
    exp_smoothing_pred_test = exp_smoothing_pred_test.fillna(0)

    meta_features_test = np.column_stack(
        (rf_pred_test, gb_pred_test, sarima_pred_test, exp_smoothing_pred_test, prophet_pred_test, lstm_pred_test))

    # Verificando se temos algum valor NaN
    meta_features_test = np.nan_to_num(meta_features_test)

    meta_prediction = model_meta.predict(meta_features_test)


    results[ticker] = {
        'valor_real_2022': df_test["receita_liquida"].values[0],
        'meta_predicao_2022': meta_prediction[0],
    }

    # Salvar os resultados como um arquivo json
    with open('../JSONS/results.json', 'w') as f:
        json.dump(results, f)

print('finalizado modelo 4 para ticker')

