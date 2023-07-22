import numpy as np
import pandas as pd
import json
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from prophet import Prophet
from keras.models import Sequential
from keras.layers import LSTM, Dense
from math import sqrt

from facade import conexao_pg

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.float32):
            return float(obj)
        return json.JSONEncoder.default(self, obj)
# Conexão com o PostgreSQL
conn = conexao_pg()

def modelagem():
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
        df_ticker = df[df['acao'] == ticker]

        if df_ticker.shape[0] <= 3 or df_ticker['receita_liquida'].nunique() <= 1:
            continue

        df_train = df_ticker[df_ticker['ano'].dt.year < 2022]
        df_test = df_ticker[df_ticker['ano'].dt.year == 2022]

        if df_test.shape[0] == 0:
            continue

        # Ajuste de hiperparâmetros
        param_grid = {'n_estimators': [50, 100, 200], 'max_depth': [None, 5, 10, 15], 'min_samples_split': [2, 5, 10]}
        model_rf = GridSearchCV(RandomForestRegressor(), param_grid)
        model_rf.fit(df_train[features], df_train['receita_liquida'])

        param_grid = {'n_estimators': [50, 100, 200], 'learning_rate': [0.1, 0.05, 0.01], 'max_depth': [3, 5, 10]}
        model_gb = GridSearchCV(GradientBoostingRegressor(), param_grid)
        model_gb.fit(df_train[features], df_train['receita_liquida'])

        model_sarima = SARIMAX(df_train['receita_liquida'], order=(1, 1, 1))
        model_sarima = model_sarima.fit(disp=False)

        model_exp_smoothing = ExponentialSmoothing(df_train['receita_liquida'])
        model_exp_smoothing = model_exp_smoothing.fit()

        model_prophet = Prophet()
        model_prophet.fit(df_train.rename(columns={'ano': 'ds', 'receita_liquida': 'y'}))

        n_features = len(features)
        n_steps = len(df_train.index.values)
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_train = scaler.fit_transform(df_train[features])

        X, y = scaled_train.reshape((n_steps, 1, n_features)), df_train['receita_liquida']

        model_lstm = Sequential()
        model_lstm.add(LSTM(50, activation='relu', input_shape=(1, n_features)))
        model_lstm.add(Dense(1))
        model_lstm.compile(optimizer='adam', loss='mse')

        model_lstm.fit(X, y, epochs=200, verbose=0)

        # Fazendo previsões
        rf_pred = model_rf.predict(df_test[features])
        gb_pred = model_gb.predict(df_test[features])
        sarima_pred = model_sarima.predict(start=len(df_train), end=len(df_train))
        exp_smoothing_pred = model_exp_smoothing.predict(start=len(df_train), end=len(df_train))
        prophet_pred = model_prophet.predict(df_test.rename(columns={'ano': 'ds'}))['yhat'].values
        scaled_test = scaler.transform(df_test[features])
        lstm_pred = model_lstm.predict(scaled_test.reshape(-1, 1, n_features))

        # Verificando se temos algum valor NaN
        lstm_pred = np.nan_to_num(lstm_pred)
        sarima_pred = sarima_pred.values.flatten()
        exp_smoothing_pred = exp_smoothing_pred.values.flatten()


        # Combinação de modelos
        meta_train_features = np.array([model_rf.predict(df_train[features]).flatten(),
                                        model_gb.predict(df_train[features]).flatten(),
                                        model_sarima.predict(start=0, end=len(df_train) - 1).values.flatten(),
                                        model_exp_smoothing.predict(start=0, end=len(df_train) - 1).values.flatten(),
                                        model_prophet.predict(df_train.rename(columns={'ano': 'ds'}))[
                                            'yhat'].values.flatten(),
                                        model_lstm.predict(
                                            df_train[features].values.reshape(-1, 1, n_features)).flatten()]).T

        # Verificando se temos algum valor NaN
        meta_train_features = np.nan_to_num(meta_train_features)

        model_meta = LinearRegression().fit(meta_train_features, df_train["receita_liquida"])

        # Agora podemos usar o modelo_meta para prever os valores do conjunto de teste
        meta_test_features = np.array([rf_pred.flatten(), gb_pred.flatten(), sarima_pred.flatten(),
                                       exp_smoothing_pred.flatten(), prophet_pred.flatten(), lstm_pred.flatten()]).T
        meta_prediction = model_meta.predict(meta_test_features)

        # Calculando métricas de erro
        MAE_rf = mean_absolute_error(df_test["receita_liquida"].values, rf_pred)
        RMSE_rf = sqrt(mean_squared_error(df_test["receita_liquida"].values, rf_pred))

        MAE_gb = mean_absolute_error(df_test["receita_liquida"].values, gb_pred)
        RMSE_gb = sqrt(mean_squared_error(df_test["receita_liquida"].values, gb_pred))

        MAE_sarima = mean_absolute_error(df_test["receita_liquida"].values, sarima_pred)
        RMSE_sarima = sqrt(mean_squared_error(df_test["receita_liquida"].values, sarima_pred))

        MAE_exp_smoothing = mean_absolute_error(df_test["receita_liquida"].values, exp_smoothing_pred)
        RMSE_exp_smoothing = sqrt(mean_squared_error(df_test["receita_liquida"].values, exp_smoothing_pred))

        MAE_prophet = mean_absolute_error(df_test["receita_liquida"].values, prophet_pred)
        RMSE_prophet = sqrt(mean_squared_error(df_test["receita_liquida"].values, prophet_pred))

        MAE_lstm = mean_absolute_error(df_test["receita_liquida"].values, lstm_pred)
        RMSE_lstm = sqrt(mean_squared_error(df_test["receita_liquida"].values, lstm_pred))

        MAE_meta = mean_absolute_error(df_test["receita_liquida"].values, meta_prediction)
        RMSE_meta = sqrt(mean_squared_error(df_test["receita_liquida"].values, meta_prediction))

        # Salvando resultados
        results[ticker] = {
            "valor_real_2022": df_test["receita_liquida"].values[0],
            "RandomForest": rf_pred[0],
            "GradientBoosting": gb_pred[0],
            "SARIMAX": sarima_pred[0] if sarima_pred.size != 0 else np.nan,
            "ExponentialSmoothing": exp_smoothing_pred[0] if exp_smoothing_pred.size != 0 else np.nan,
            "Prophet": prophet_pred[0],
            "LSTM": lstm_pred[0][0],
            "meta_predicao_2022": meta_prediction[0]
        }

        # Calcular o MAE e o RMSE para cada modelo e a previsão da meta
        metric_results = {}
        for model in ["RandomForest", "GradientBoosting", "SARIMAX", "ExponentialSmoothing", "Prophet", "LSTM",
                      "meta_predicao_2022"]:
            # Coleta apenas os resultados que possuem um "valor_real_2022" e um valor para o modelo especificado
            valid_results = [result for result in results.values() if "valor_real_2022" in result and model in result]

            y_true = [result["valor_real_2022"] for result in valid_results]
            y_pred = [result[model] for result in valid_results]

            mae = mean_absolute_error(y_true, y_pred)
            rmse = np.sqrt(mean_squared_error(y_true, y_pred))
            metric_results[model] = {"MAE": float(mae), "RMSE": float(rmse)}  # convertendo para float padrão

        # Adicionando as métricas de erro ao dicionário results
        results['metricas'] = metric_results

        # Salvando os resultados em um arquivo json
        with open('../JSONS/resultado_predicoes.json', 'w') as f:
            json.dump(results, f, cls=JSONEncoder)


if __name__ == "__main__":
    modelagem()