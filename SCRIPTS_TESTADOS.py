import time

import gspread
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.statespace.sarimax import SARIMAX


def model_receita(receita):
    # Converte a lista de receitas em uma Series do pandas
    receita = pd.Series(receita, index=pd.date_range(start='2013', periods=len(receita), freq='Y'))

    # Preenche os valores ausentes com a média da receita
    receita = receita.fillna(receita.mean())

    # Decompõe a série em tendência, sazonalidade e resíduo
    result = seasonal_decompose(receita, model='multiplicative')

    # Ajusta um modelo SARIMA
    model_sarima = SARIMAX(receita, order=(1, 1, 1))
    model_sarima = model_sarima.fit(disp=False)

    # Ajusta um modelo de Suavização Exponencial
    model_exp_smoothing = ExponentialSmoothing(receita)
    model_exp_smoothing = model_exp_smoothing.fit()

    return model_sarima, model_exp_smoothing


# Para usar a função acima, você pode fazer algo assim:
receita = [104582220000, 137778600000, 182368880000, 168040000000, 147064450000,
           120378690000, 128490560000, 97128450000, 134680710000, 236549060000, 253968370000]

model_sarima, model_exp_smoothing = model_receita(receita)

# Você pode usar os modelos para fazer previsões
sarima_forecast = model_sarima.forecast(steps=5)
exp_smoothing_forecast = model_exp_smoothing.forecast(steps=5)


def verifica_receita_crescente_ARIMA(gc, sheet_id, tickers):
    # Abre a guia "Açoes"
    acoes_sheet = gc.open_by_key(sheet_id).worksheet('Açoes')

    # Busca a posição (linha) de cada ticker na guia "Açoes"
    ticker_rows = {ticker: acoes_sheet.find(ticker).row for ticker in tickers}

    # Cria uma lista vazia para guardar as células a serem atualizadas
    cells_to_update = []

    for ticker in tickers:
        # Abre a guia com o nome do ticker
        ticker_sheet = gc.open_by_key(sheet_id).worksheet(ticker)

        # Pega os valores da receita dos últimos cinco anos (2018 a 2022)
        receita = ticker_sheet.col_values(2)[1:12]  # B2 até B12

        # Converte a receita para inteiros, tratando valores ausentes
        receita = [int(x.replace('.', '')) if x != '' and x != '-' else None for x in receita]

        # Se a lista estiver vazia, a tendência não pode ser calculada
        if all(x is None for x in receita):
            # Cria uma célula com a resposta "NAO"
            cell = gspread.Cell(row=ticker_rows[ticker], col=8, value="NAO")
            time.sleep(1)
            cells_to_update.append(cell)
        else:
            # Converte para DataFrame e interpola os valores ausentes
            receita_df = pd.DataFrame(receita, columns=['Receita'])
            receita_df = receita_df.interpolate()

            # Aplica o modelo ARIMA aos dados da receita
            model = ARIMA(receita_df['Receita'], order=(5, 1, 0))
            model_fit = model.fit()

            # Imprime os coeficientes AR do modelo
            print(f"AR coefficients for {ticker}: {model_fit.arparams}")

            # Verifica se a tendência é positiva (crescente)
            crescente = model_fit.arparams[0] > 0

            # Cria uma célula com a resposta ("SIM" se a receita for crescente ou estável, "NAO" caso contrário)
            # cell = gspread.models.Cell(row=ticker_rows[ticker], col=8, value="SIM" if crescente else "NAO")
            cell = Cell(row=ticker_rows[ticker], col=8, value="SIM" if crescente else "NAO")

            cells_to_update.append(cell)

    # Atualiza todas as células de uma vez
    acoes_sheet.update_cells(cells_to_update)


def verifica_receita_crescente_BASICO(gc, sheet_id, tickers):
    # Abre a guia "Açoes"
    acoes_sheet = gc.open_by_key(sheet_id).worksheet('Açoes')

    # Busca a posição (linha) de cada ticker na guia "Açoes"
    ticker_rows = {ticker: acoes_sheet.find(ticker).row for ticker in tickers}

    # Cria uma lista vazia para guardar as células a serem atualizadas
    cells_to_update = []

    for ticker in tickers:
        time.sleep(1)  # Pause entre as solicitações para evitar ultrapassar a cota da API.
        # Abre a guia com o nome do ticker
        ticker_sheet = gc.open_by_key(sheet_id).worksheet(ticker)

        # Pega os valores da receita dos últimos cinco anos (2018 a 2022)
        receita = ticker_sheet.col_values(2)[1:12]  # B2 até B12

        # Converte a receita para inteiros, tratando valores ausentes
        receita = [int(x.replace('.', '')) if x != '' and x != '-' else None for x in receita]

        # Se a lista estiver vazia, a tendência não pode ser calculada
        if all(x is None for x in receita):
            # Cria uma célula com a resposta "NAO"
            cell = gspread.Cell(row=ticker_rows[ticker], col=8, value="NAO")
            cells_to_update.append(cell)
        else:
            # Filtra os valores None da lista receita
            receita = [x for x in receita if x is not None]

            # Verifica se a receita é crescente ou estável
            crescente = all(i <= j for i, j in zip(receita, receita[1:]))

            # Cria uma célula com a resposta ("SIM" se a receita for crescente ou estável, "NAO" caso contrário)
            cell = gspread.Cell(row=ticker_rows[ticker], col=8, value="SIM" if crescente else "NAO")
            cells_to_update.append(cell)

    # Atualiza todas as células de uma vez
    acoes_sheet.update_cells(cells_to_update)


def verifica_receita_crescente_SARIMA_1(gc, sheet_id, tickers):
    acoes_sheet = gc.open_by_key(sheet_id).worksheet('Açoes')

    ticker_rows = {ticker: acoes_sheet.find(ticker).row for ticker in tickers}

    ticker_sheets = []  # Lista para armazenar as planilhas correspondentes a cada ticker

    for ticker in tickers:
        ticker_sheet = gc.open_by_key(sheet_id).worksheet(ticker)
        ticker_sheets.append(ticker_sheet)  # Adiciona a planilha à lista

    cells_to_update = []

    for ticker, ticker_sheet in zip(tickers, ticker_sheets):
        receita = ticker_sheet.col_values(2)[1:12]
        receita = [int(x.replace('.', '')) if x != '' and x != '-' else None for x in receita]

        if all(x is None for x in receita):
            cell = gspread.Cell(row=ticker_rows[ticker], col=8, value="NAO")
            cells_to_update.append(cell)
        else:
            receita = [x for x in receita if x is not None]
            receita = np.array(receita).astype(float)  # Convert the list to a numpy array

            # Fit the SARIMA model
            model = SARIMAX(receita, order=(1, 1, 1), seasonal_order=(1, 1, 0, 12))
            model_fit = model.fit(disp=False)

            # Check if the AR coefficient is positive
            crescente = model_fit.params[0] > 0

            cell = gspread.Cell(row=ticker_rows[ticker], col=8, value="SIM" if crescente else "NAO")
            cells_to_update.append(cell)

    acoes_sheet.update_cells(cells_to_update)


def verifica_receita_crescente(gc, sheet_id, tickers):
    acoes_sheet = gc.open_by_key(sheet_id).worksheet('Açoes')
    ticker_rows = {ticker: acoes_sheet.find(ticker).row for ticker in tickers}

    ticker_sheets = []
    for ticker in tickers:
        ticker_sheet = gc.open_by_key(sheet_id).worksheet(ticker)
        ticker_sheets.append(ticker_sheet)

    cells_to_update = []
    for ticker, ticker_sheet in zip(tickers, ticker_sheets):
        receita = ticker_sheet.col_values(2)[1:12]
        receita = [int(x.replace('.', '')) if x != '' and x != '-' else None for x in receita]

        if all(x is None for x in receita):
            cell = gspread.Cell(row=ticker_rows[ticker], col=8, value="NAO")
            cells_to_update.append(cell)
        else:
            receita = [x for x in receita if x is not None]
            receita = np.array(receita).astype(float)

            model_sarima, model_exp_smoothing = model_receita(receita)

            # Previsões para os próximos 5 anos
            sarima_forecast = model_sarima.forecast(steps=5)
            exp_smoothing_forecast = model_exp_smoothing.forecast(steps=5)

            # Verifica se a previsão da receita para o próximo ano é maior que a receita do ano atual
            crescente_sarima = sarima_forecast[0] > receita[-1]
            crescente_exp_smoothing = exp_smoothing_forecast[0] > receita[-1]

            # Se qualquer um dos modelos prevê um aumento na receita, define crescente como True
            crescente = crescente_sarima or crescente_exp_smoothing

            cell = gspread.Cell(row=ticker_rows[ticker], col=8, value="SIM" if crescente else "NAO")
            cells_to_update.append(cell)

    acoes_sheet.update_cells(cells_to_update)


def verifica_roic(gc, sheet_id, tickers, col_acoes, col_ticker, window=3):
    acoes_sheet = gc.open_by_key(sheet_id).worksheet('Açoes')

    ticker_rows = {ticker: acoes_sheet.find(ticker).row for ticker in tickers}

    ticker_sheets = []
    for ticker in tickers:
        ticker_sheet = gc.open_by_key(sheet_id).worksheet(ticker)
        ticker_sheets.append(ticker_sheet)

    cells_to_update = []

    for ticker, ticker_sheet in zip(tickers, ticker_sheets):
        data = ticker_sheet.col_values(col_ticker)[1:12]
        data = [float(x.replace('%', '').replace(',', '.')) / 100 if x != '' and x != '-' else None for x in data]

        if all(x is None for x in data):
            cell = gspread.Cell(row=ticker_rows[ticker], col=col_acoes, value="NAO")
            cells_to_update.append(cell)
        else:
            # calcula a média móvel
            moving_averages = [
                sum(val for val in data[i - window:i] if val is not None) / window if i >= window else None for i in
                range(len(data))]
            roic_15 = all(x is None or x >= 0.15 for x in moving_averages)
            cell = gspread.Cell(row=ticker_rows[ticker], col=col_acoes, value="SIM" if roic_15 else "NAO")
            cells_to_update.append(cell)

    acoes_sheet.update_cells(cells_to_update)


def modela_e_verifica_crescente(gc, sheet_id, tickers, campo, col_acoes, col_ticker):
    acoes_sheet = gc.open_by_key(sheet_id).worksheet('Açoes')

    ticker_rows = {ticker: acoes_sheet.find(ticker).row for ticker in tickers}

    ticker_sheets = []
    for ticker in tickers:
        ticker_sheet = gc.open_by_key(sheet_id).worksheet(ticker)
        ticker_sheets.append(ticker_sheet)

    cells_to_update = []

    for ticker, ticker_sheet in zip(tickers, ticker_sheets):
        data = ticker_sheet.col_values(col_ticker)[1:12]
        data = [int(x.replace('.', '')) if x != '' and x != '-' else None for x in data]

        if all(x is None for x in data):
            cell = gspread.Cell(row=ticker_rows[ticker], col=col_acoes, value="NAO")
            cells_to_update.append(cell)
        else:
            data = [x for x in data if x is not None]
            data = np.array(data).astype(float)

            model_sarima, model_exp_smoothing = model_receita(data)

            sarima_forecast = model_sarima.forecast(steps=5)
            exp_smoothing_forecast = model_exp_smoothing.forecast(steps=5)

            crescente_sarima = sarima_forecast[0] > data[-1]
            crescente_exp_smoothing = exp_smoothing_forecast[0] > data[-1]

            crescente = crescente_sarima or crescente_exp_smoothing

            cell = gspread.Cell(row=ticker_rows[ticker], col=col_acoes, value="SIM" if crescente else "NAO")
            cells_to_update.append(cell)

    acoes_sheet.update_cells(cells_to_update)


def model_receita(receita):
    receita = pd.Series(receita, index=pd.date_range(start='2010', periods=len(receita), freq='Y'))
    receita = receita.fillna(receita.mean())

    # Prepare os dados para o Prophet
    df = receita.reset_index()
    df.columns = ['ds', 'y']

    # Modelo Prophet
    model_prophet = Prophet()
    model_prophet.fit(df)

    model_sarima = SARIMAX(receita, order=(1, 1, 1))
    model_sarima = model_sarima.fit(disp=False)

    model_exp_smoothing = ExponentialSmoothing(receita)
    model_exp_smoothing = model_exp_smoothing.fit()

    return model_sarima, model_exp_smoothing, model_prophet


def get_dados_fundamentalistas_selenium_b3(navegador, ticker):
    navegador.switch_to.frame('bvmf_iframe')

    # Nome empresa
    nome_emp = navegador.find_element(By.XPATH,
                                      "/html/body/app-root/app-companies-home/div/div/div/div/div[1]/div[2]/div/app-companies-home-filter-name/form/div/div[1]/input")
    nome_emp.send_keys(ticker)

    # Bucas
    navegador.find_element(By.XPATH,
                           "/html/body/app-root/app-companies-home/div/div/div/div/div[1]/div[2]/div/app-companies-home-filter-name/form/div/div[3]/button").click()

    # Seleciona o papel
    WebDriverWait(navegador, 10).until(EC.presence_of_element_located(
        (By.XPATH, "/html/body/app-root/app-companies-search/div/form/div[2]/div[1]/div/div/div"))).click()

    # Seleciona os relatórios
    WebDriverWait(navegador, 10).until(EC.presence_of_element_located(
        (By.XPATH, "/html/body/app-root/app-companies-menu-select/div/div/div[2]/form/select"))).click()

    select_report = Select(navegador.find_element(By.XPATH,
                                                  '/html/body/app-root/app-companies-menu-select/div/div/div[2]/form/select'))  # Localiza o elemento select
    select_report.select_by_value('reports')

    select_year = Select(navegador.find_element(By.XPATH,
                                                '/html/body/app-root/app-companies-menu-select/div/app-companies-structured-reports/form/div[1]/div/div/select'))

    # Obtenha todos os elementos option dentro do elemento select
    options = select_year.options

    # Extraia os valores dos elementos option para obter os anos disponíveis
    anos_disponiveis = [option.get_attribute('value') for option in options]

    for ano in anos_disponiveis:
        ano_atual = str(datetime.now().year)
        if ano == ano_atual:
            link_text = f" 31/12/{int(ano) - 1} - Demonstrações Financeiras Padronizadas "

            # Procura o link com o texto especificado
            link_element = navegador.find_element(By.XPATH, f"//a[contains(text(), '{link_text}')]")

            # Acessa o link
            link_element.click()

            navegador.switch_to.frame('iFrameFormulariosFilho')


# login
navegador.maximize_window()
url = "https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/renda-variavel/empresas-listadas.htm"
navegador.get(url)
for ticker in tickers:
    b3 = get_dados_fundamentalistas_selenium_b3(navegador, ticker)
    insere_pg(b3, ticker)
    tickers_processed.append(ticker)
    with open('JSONS/tickers_processed.json', 'w') as f:
        json.dump(tickers_processed, f)

login = login_inv_10(navegador, url="https://investidor10.com.br/")

if login:
    for ticker in tickers:
        try:
            url = f"https://investidor10.com.br/acoes/{ticker}/"
            navegador.get(url)
            dados = get_dados_fundamentalistas_selenium(navegador)
            # dados = {'2022': ['236.549.060.000', '162.202.490.000', '74.346.570.000', '29.849.330.000', '', '38.301.720.000', '8.452.380.000', '', '', '31,43', '0,00', '12,62', '18,78', '18,78'], '2021': ['134.680.710.000', '90.857.410.000', '47.714.170.000', '17.678.970.000', '', '20.068.130.000', '1.186.770.000', '', '', '35,43', '0,00', '13,13', '12,38', '13,23'], '2020': ['97.128.450.000', '109.253.600.000', '17.286.870.000', '12.512.160.000', '3.134.540.000', '7.336.900.000', '4.555.150.000', '', '', '17,80', '3,23', '12,88', '10,72', '2,38'], '2019': ['128.490.560.000', '100.728.960.000', '27.761.600.000', '17.899.347.000', '', '8.584.720.000', '7.748.800.000', '', '', '21,61', '0,00', '13,93', '0,00', '0,00'], '2018': ['120.378.690.000', '82.160.830.000', '38.217.870.000', '15.086.100.000', '', '20.414.200.000', '5.328.090.000', '', '', '31,75', '0,00', '12,53', '0,00', '0,00'], '2017': ['147.064.450.000', '115.724.700.000', '31.339.750.000', '12.275.300.000', '', '15.930.470.000', '3.655.160.000', '', '', '21,31', '0,00', '8,35', '0,00', '0,00'], '2016': ['168.040.000.000', '134.530.000.000', '33.510.000.000', '8.660.000.000', '', '10.890.000.000', '2.230.000.000', '', '', '19,94', '0,00', '5,15', '0,00', '0,00'], '2015': ['182.368.880.000', '159.904.030.000', '22.464.840.000', '15.798.040.000', '', '10.137.510.000', '9.235.330.000', '', '', '12,32', '0,00', '8,66', '0,00', '0,00'], '2014': ['137.778.600.000', '105.909.420.000', '31.869.180.000', '13.343.500.000', '', '15.604.520.000', '2.261.020.000', '', '', '23,13', '0,00', '9,68', '0,00', '0,00'], '2013': ['104.582.220.000', '74.376.890.000', '30.205.330.000', '1.576.844.000', '', '12.858.990.000', '1.570.160.000', '', '', '28,88', '0,00', '1,51', '0,00', '0,00'], '2012': ['94.180.850.000', '63.992.040.000', '30.188.810.000', '11.405.324.000', '', '15.008.760.000', '3.603.420.000', '', '', '32,05', '0,00', '12,11', '0,00', '0,00'], '2011': ['94.871.010.000', '63.989.420.000', '30.881.600.000', '13.099.370.000', '', '15.366.073.000', '5.028.300.000', '', '', '32,55', '0,00', '13,81', '0,00', '0,00'], '2010': ['85.143.200.000', '50.775.740.000', '34.367.460.000', '11.330.340.000', '', '16.550.870.000', '5.220.520.000', '', '', '40,36', '0,00', '13,31', '0,00', '0,00']}
            insere_pg(dados, ticker)

            # Adiciona o ticker à lista de tickers processados e salva no arquivo
            tickers_processed.append(ticker)
            with open('JSONS/tickers_processed.json', 'w') as f:
                json.dump(tickers_processed, f)

        except Exception as e:
            print(f"Erro ao processar o ticker {ticker}: {str(e)}")
            continue


def modelagem():
    # Obtenção de dados
    query = "SELECT acao, ano, receita_liquida, lucro_liquido, ebitda, ebit, margem_liquida, roe, patrimonio_liquido, payout FROM public.acoes_contabil"
    df = pd.read_sql(query, conn)
    df['ano'] = pd.to_datetime(df['ano'], format='%Y')

    tickers = df['acao'].unique()
    results = {}

    # Feature Engineering
    features = ['lucro_liquido', 'ebitda', 'ebit', 'margem_liquida', 'roe', 'patrimonio_liquido', 'payout']

    for ticker in tickers:
        df_ticker = df[df['acao'] == ticker]

        if df_ticker.shape[0] <= 3 or df_ticker['receita_liquida'].nunique() <= 1:
            continue

        df_train = df_ticker[df_ticker['ano'].dt.year < 2022]
        df_test = df_ticker[df_ticker['ano'].dt.year == 2022]

        if df_test.shape[0] == 0:
            continue

        model_exp_smoothing = ExponentialSmoothing(df_train['receita_liquida'])
        model_exp_smoothing = model_exp_smoothing.fit()

        model_prophet = Prophet()
        model_prophet.fit(df_train.rename(columns={'ano': 'ds', 'receita_liquida': 'y'}))

        # Fazendo previsões
        exp_smoothing_pred = model_exp_smoothing.predict(start=len(df_train), end=len(df_train))
        prophet_pred = model_prophet.predict(df_test.rename(columns={'ano': 'ds'}))['yhat'].values

        exp_smoothing_pred = exp_smoothing_pred.values.flatten()

        # Combinação de modelos
        meta_train_features = np.array([model_exp_smoothing.predict(start=0, end=len(df_train) - 1).values.flatten(),
                                        model_prophet.predict(df_train.rename(columns={'ano': 'ds'}))[
                                            'yhat'].values.flatten()]).T

        # Verificando se temos algum valor NaN
        meta_train_features = np.nan_to_num(meta_train_features)

        model_meta = LinearRegression().fit(meta_train_features, df_train["receita_liquida"])

        # Agora podemos usar o modelo_meta para prever os valores do conjunto de teste
        meta_test_features = np.array([exp_smoothing_pred.flatten(), prophet_pred.flatten()]).T
        meta_prediction = model_meta.predict(meta_test_features)

        # Calculando métricas de erro
        MAE_exp_smoothing = mean_absolute_error(df_test["receita_liquida"].values, exp_smoothing_pred)
        RMSE_exp_smoothing = sqrt(mean_squared_error(df_test["receita_liquida"].values, exp_smoothing_pred))

        MAE_prophet = mean_absolute_error(df_test["receita_liquida"].values, prophet_pred)
        RMSE_prophet = sqrt(mean_squared_error(df_test["receita_liquida"].values, prophet_pred))

        MAE_meta = mean_absolute_error(df_test["receita_liquida"].values, meta_prediction)
        RMSE_meta = sqrt(mean_squared_error(df_test["receita_liquida"].values, meta_prediction))

        # Salvando resultados
        results[ticker] = {
            "valor_real_2022": df_test["receita_liquida"].values[0],
            "ExponentialSmoothing": exp_smoothing_pred[0] if exp_smoothing_pred.size != 0 else np.nan,
            "Prophet": prophet_pred[0],
            "meta_predicao_2022": meta_prediction[0]
        }

        # Calcular o MAE e o RMSE para cada modelo e a previsão da meta
        metric_results = {}
        for model in ["ExponentialSmoothing", "Prophet", "meta_predicao_2022"]:
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
        with open('JSONS/resultado_predicoes.json', 'w') as f:
            json.dump(results, f, cls=JSONEncoder)


def modelagem_2(target):
    # Obtenção de dados
    query = "SELECT acao, ano, receita_liquida, lucro_liquido, ebitda, ebit, margem_liquida, roe, patrimonio_liquido, payout FROM public.acoes_contabil"
    df = pd.read_sql(query, conn)
    df['ano'] = pd.to_datetime(df['ano'], format='%Y')
    ano_atual = datetime.now().year

    tickers = df['acao'].unique()
    results = {}

    for ticker in tickers:
        df_ticker = df[df['acao'] == ticker]

        if df_ticker.shape[0] <= 3 or df_ticker[target].nunique() <= 1:
            continue

        df_train = df_ticker[df_ticker['ano'].dt.year < ano_atual]
        df_test = df_ticker[df_ticker['ano'].dt.year == ano_atual - 1]

        if df_test.shape[0] == 0:
            continue

        model_exp_smoothing = ExponentialSmoothing(df_train[target])
        model_exp_smoothing = model_exp_smoothing.fit()

        model_prophet = Prophet()
        model_prophet.fit(df_train.rename(columns={'ano': 'ds', target: 'y'}))

        # Fazendo previsões
        exp_smoothing_pred = model_exp_smoothing.predict(start=len(df_train), end=len(df_train))
        prophet_pred = model_prophet.predict(df_test.rename(columns={'ano': 'ds'}))['yhat'].values

        exp_smoothing_pred = exp_smoothing_pred.values.flatten()

        # Combinação de modelos
        meta_train_features = np.array([model_exp_smoothing.predict(start=0, end=len(df_train) - 1).values.flatten(),
                                        model_prophet.predict(df_train.rename(columns={'ano': 'ds'}))[
                                            'yhat'].values.flatten()]).T

        # Verificando se temos algum valor NaN
        meta_train_features = np.nan_to_num(meta_train_features)

        model_meta = LinearRegression().fit(meta_train_features, df_train[target])

        # Agora podemos usar o modelo_meta para prever os valores do conjunto de teste
        meta_test_features = np.array([exp_smoothing_pred.flatten(), prophet_pred.flatten()]).T
        meta_prediction = model_meta.predict(meta_test_features)

        # Categorizando as previsões
        last_year_value = df_train[target].values[-1]
        pred_value = meta_prediction[0]

        if pred_value > last_year_value * 1.05:
            category = 'SIM'  # crescimento
        elif last_year_value * 0.95 <= pred_value <= last_year_value * 1.05:
            category = 'ESTABILIDADE'  # estabilidade
        else:
            category = 'NAO'  # queda

        # Salvando resultados
        results[ticker] = {
            "modelo": category
        }

    # Insere os resultados no banco de dados
    for ticker, category in results.items():
        insert_query = f"UPDATE public.acoes SET {target} = '{category['modelo']}' WHERE ticker = '{ticker}'"
        cur = conn.cursor()
        cur.execute(insert_query)
        conn.commit()


def modelagem_3(target):
    # Obtenção de dados
    query = "SELECT acao, ano, receita_liquida, lucro_liquido, ebitda, ebit, margem_liquida, roe, patrimonio_liquido, payout FROM public.acoes_contabil"
    df = pd.read_sql(query, conn)
    df['ano'] = pd.to_datetime(df['ano'], format='%Y')
    ano_atual = datetime.now().year

    # Definir o número de anos a serem considerados
    num_years = 5

    # Obter a lista de ações únicas
    tickers = df['acao'].unique()

    # Inicializar um dicionário para armazenar os resultados
    results = {}

    # Treinar um modelo para cada ação
    for ticker in tickers:
        df_ticker = df[df['acao'] == ticker]
        data_last_years = df_ticker[df_ticker['ano'].dt.year.isin(range(ano_atual - num_years, ano_atual + 1))]

        # Computar a taxa média de crescimento
        growth_rates = (data_last_years[target].values[1:] / data_last_years[target].values[:-1]) - 1
        avg_growth_rate = np.mean(growth_rates)

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
                category += f' (previsão: {meta_prediction[0]:.2f})'

        # Armazenar o resultado
        results[ticker] = {
            'modelo': category,
            'taxa_media_crescimento': avg_growth_rate
        }

    # Inserir os resultados no banco de dados
    for ticker, result in results.items():
        insert_query = f"UPDATE public.acoes SET {target} = '{result['modelo']}' WHERE ticker = '{ticker}'"
        cur = conn.cursor()
        cur.execute(insert_query)
        conn.commit()


def model_receita(receita, anos):
    start_year = min(anos)
    receita = pd.Series(receita, index=pd.date_range(start=str(start_year), periods=len(receita), freq='Y'))
    receita = receita.fillna(receita.mean())

    # Prepare os dados para o Prophet
    df = receita.reset_index()
    df.columns = ['ds', 'y']

    # Modelo Prophet
    model_prophet = Prophet()
    model_prophet.fit(df)

    # Modelo SARIMAX, somente se houver dados suficientes
    if len(receita) >= 3:
        model_sarima = SARIMAX(receita, order=(1, 1, 1))
        model_sarima = model_sarima.fit(disp=False)
    else:
        model_sarima = None

    model_exp_smoothing = ExponentialSmoothing(receita)
    model_exp_smoothing = model_exp_smoothing.fit()

    return model_sarima, model_exp_smoothing, model_prophet


def roic_is_ok(roic_data):
    # Inicialmente, suponha que o ROIC está OK
    roic_ok = True

    # Verifique se há mais de 2 anos com ROIC < 15%
    bad_years = [year for year, roic in roic_data.items() if roic is not None and roic < 15]

    if len(bad_years) > 3:
        roic_ok = False

    # Verifique se há algum ano ruim nos últimos 3 anos
    recent_years = sorted(roic_data.keys())[-3:]
    if any(year in bad_years for year in recent_years):
        roic_ok = False

    return roic_ok


def modela_e_verifica_crescente(tickers, tipo, ticker_classification):
    for ticker in tickers:

        dados = get_values_contabil(ticker, tipo)

        if dados:
            anos, valores = zip(*dados)
        else:
            crescente_str = "NAO"
            motivo = "Não tem dados no banco"
            insere_classificacao_pg(crescente_str, ticker, tipo, motivo)

            # Adicione o ticker e o tipo à classificação do ticker
            ticker_classification[ticker] = tipo

            # Grave a classificação do ticker no arquivo
            with open('tickers_classification.json', 'w') as file:
                json.dump(ticker_classification, file)

            continue

        # data = pd.Series(valores, index=pd.to_datetime(anos, format='%Y'))

        if tipo == "roic":
            # Crie um dicionário de dados de ROIC com o ano como chave
            roic_data = {i + 2013: data[i] for i in range(len(data))}
            roic_ok = roic_is_ok(roic_data)
            if roic_ok:
                # Continue com a modelagem estatística se o ROIC estiver OK
                data = np.array(data).astype(float)
                model_sarima, model_exp_smoothing = model_receita(data)
                sarima_forecast = model_sarima.forecast(steps=5)
                exp_smoothing_forecast = model_exp_smoothing.forecast(steps=5)
                crescente_sarima = sarima_forecast[0] > data[-1]
                crescente_exp_smoothing = exp_smoothing_forecast[0] > data[-1]
                crescente = crescente_sarima or crescente_exp_smoothing

                cell = gspread.Cell(row=ticker_rows[ticker], col=col_acoes,
                                    value="SIM" if roic_ok and crescente else "NAO")

                cells_to_update.append(cell)
        else:
            data = np.array(valores).astype(float)
            model_sarima, model_exp_smoothing, model_prophet = model_receita(data, anos)
            if model_sarima:
                sarima_forecast = model_sarima.forecast(steps=5)
                crescente_sarima = sarima_forecast[0] > data[-1]
                if not crescente_sarima:
                    motivo = "Modelo SARIMAX previu não-crescimento"
            else:
                crescente_sarima = False
                motivo = "Insuficiente dados para modelo SARIMAX"

            exp_smoothing_forecast = model_exp_smoothing.forecast(steps=5)
            crescente_exp_smoothing = exp_smoothing_forecast[0] > data[-1]
            if not crescente_exp_smoothing:
                motivo = "Modelo ExponentialSmoothing previu não-crescimento"

            prophet_forecast = model_prophet.predict(
                pd.DataFrame({'ds': pd.date_range(start=str(max(anos) + 1), periods=5, freq='Y')}))
            crescente_prophet = prophet_forecast['yhat'][0] > data[-1]
            if not crescente_prophet:
                motivo = "Modelo Prophet previu não-crescimento"

            crescente = sum([crescente_sarima, crescente_exp_smoothing, crescente_prophet]) >= 2

            # Converta o booleano para "SIM" ou "NÃO"
            crescente_str = "SIM" if crescente else "NAO"

            insere_classificacao_pg(crescente_str, ticker, tipo, motivo)

            # Adicione o ticker e o tipo à classificação do ticker
            ticker_classification[ticker] = tipo

            # Grave a classificação do ticker no arquivo
            with open('tickers_classification.json', 'w') as file:
                json.dump(ticker_classification, file)
