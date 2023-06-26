import json
import time

import gspread
import numpy as np
import pandas as pd
from google.oauth2 import service_account
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
from webdriver_manager.chrome import ChromeDriverManager


# Estabelece a conexão com a planilha do Google
def conn_sheet():
    KEY_FILE = 'C:\\Users\\mrcr\\Documents\\projetos_python\\AcoesPrecoJusto\\acoessempre-2a81866e7af2.json'
    SHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    credentials = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SHEET_SCOPES)

    return gspread.authorize(credentials)


def login_inv_10(navegador, url):
    navegador.get(url)

    # Abrir menu
    WebDriverWait(navegador, 10).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[3]/header/div[1]/div/div[2]/a"))).click()

    # Click em entrar
    entrar = WebDriverWait(navegador, 10).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[3]/header/div[1]/div/div[2]/nav/ul/li[2]/a")))

    time.sleep(2)

    entrar.click()

    # Fazer Login
    navegador.find_element(By.XPATH, "/html/body/div[4]/div/div[1]/form/div[1]/input").send_keys("levicruz49@gmail.com")
    navegador.find_element(By.XPATH, "/html/body/div[4]/div/div[1]/form/div[2]/input").send_keys("Embraer198@")

    # Entrar
    navegador.find_element(By.XPATH, "/html/body/div[4]/div/div[1]/form/div[3]/input").click()

    img = WebDriverWait(navegador, 10).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/header/div[1]/div/div[2]/div/span/a/img")))
    alt = img.get_attribute('alt')

    if alt == 'Levi Cruz':
        return True
    else:
        return False


def get_dados_fundamentalistas_selenium(navegador):
    # Deixa o tempo para a página recarregar
    time.sleep(3)
    descer_tela = None
    xpaths_descer_tela = ["/html/body/div[2]/div/main/section/div/div[14]/div[2]",
                          "/html/body/div[2]/div/main/section/div/div[13]/div[2]",
                          "/html/body/div[2]/div/main/section/div/div[12]/div[3]",
                          ]

    for path in xpaths_descer_tela:
        try:
            descer_tela = WebDriverWait(navegador, 1).until(EC.presence_of_element_located((By.XPATH, path)))
            navegador.execute_script("arguments[0].scrollIntoView(true);", descer_tela)
            break
        except Exception as e:
            print(f"Failed to find element with xpath {path}. Error: {e}")

    if not descer_tela:
        print("Failed to find element with any of the provided xpaths.")

    time.sleep(3)

    xpaths_menu_anos = [
        "/html/body/div[2]/div/main/section/div/div[14]/div[3]/div[1]/div/ul/li[5]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[14]/div[2]/div[1]/div/ul/li[5]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[13]/div[2]/div[1]/div/ul/li[5]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[12]/div[3]/div[1]/div/ul/li[5]/span/span[1]/span/span[1]"]

    for path in xpaths_menu_anos:
        try:
            menu_anos = WebDriverWait(navegador, 1).until(EC.presence_of_element_located((By.XPATH, path)))
            time.sleep(1)
            menu_anos.click()
            break
        except Exception as e:
            print(f"Failed to find element with xpath {path}. Error: {e}")

    # Seleciona 10 ANOS
    try:
        elemento_ano = navegador.find_element(By.XPATH, '/html/body/span/span/span[2]/ul/li[4]')
    except:
        elemento_ano = navegador.find_element(By.XPATH, '/html/body/span/span/span[2]/ul/li[4]')

    elemento_ano.click()
    time.sleep(1)

    xpaths_val_detalhados = [
        "/html/body/div[2]/div/main/section/div/div[14]/div[3]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[14]/div[2]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[13]/div[2]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[12]/div[3]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]"]

    for path in xpaths_val_detalhados:
        try:
            val_detalhados = WebDriverWait(navegador, 1).until(EC.presence_of_element_located((By.XPATH, path)))
            time.sleep(1)
            val_detalhados.click()
            break
        except Exception as e:
            print(f"Failed to find element with xpath {path}. Error: {e}")

    # Seleciona os valores como detalhados
    navegador.find_element(By.XPATH, "/html/body/span/span/span[2]/ul/li[2]").click()

    table = navegador.find_element(By.ID, 'table-balance-results')
    rows = table.find_elements(By.TAG_NAME, 'tr')

    data = []
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, 'td')
        row_data = [cell.text for cell in cells]
        data.append(row_data)

    dados = []
    for row_data in data:
        # Ignorar lista vazia
        if not row_data:
            continue

        row_data_without_spaces = list(filter(bool, row_data))
        row_data_without_spaces[0] = row_data_without_spaces[0].replace(' 0', '').replace('-', '').strip()
        row_data_without_spaces = [element.replace('(R$)', '').replace('R$', '').replace('(%)', '').strip() for element
                                   in row_data_without_spaces]
        dados.append(row_data_without_spaces)

    return dados


def preencher_sheets(navegador, ticker, sheet):
    url = f"https://investidor10.com.br/acoes/{ticker[0]}/"
    navegador.get(url)
    dados = get_dados_fundamentalistas_selenium(navegador)

    for i, row_data in enumerate(dados):
        # Remove o primeiro elemento da linha (o nome do campo)
        row_data = row_data[1:]

        # Inverte a ordem dos dados
        row_data.reverse()

        # Atualiza as colunas B-O com os valores dos dados
        cells = sheet.range(f'{chr(66 + i)}2:{chr(66 + i)}{1 + len(row_data)}')
        for j, cell in enumerate(cells):
            cell.value = row_data[j]
        sheet.update_cells(cells)


def model_receita(receita):
    receita = pd.Series(receita, index=pd.date_range(start='2013', periods=len(receita), freq='Y'))
    receita = receita.fillna(receita.mean())

    model_sarima = SARIMAX(receita, order=(1, 1, 1))
    model_sarima = model_sarima.fit(disp=False)

    model_exp_smoothing = ExponentialSmoothing(receita)
    model_exp_smoothing = model_exp_smoothing.fit()

    return model_sarima, model_exp_smoothing


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


def modela_e_verifica_crescente_2(gc, sheet_id, tickers, col_acoes, col_ticker):
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
            if None in data:
                # Preenche campos vazios com None
                data = [x if x is not None else None for x in data]

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


def modela_e_verifica_crescente(gc, sheet_id, tickers, modelo ,col_acoes, col_ticker):
    acoes_sheet = gc.open_by_key(sheet_id).worksheet('Açoes')

    ticker_rows = {ticker: acoes_sheet.find(ticker).row for ticker in tickers}

    ticker_sheets = []
    for ticker in tickers:
        ticker_sheet = gc.open_by_key(sheet_id).worksheet(ticker)
        ticker_sheets.append(ticker_sheet)

    cells_to_update = []

    for ticker, ticker_sheet in zip(tickers, ticker_sheets):
        data = ticker_sheet.col_values(col_ticker)[1:12]
        # data = [float(x.strip('%')) if x != '' and x != '-' else None for x in data]
        data = [float(x.replace(',', '.').strip('% ').replace('-', '0')) if x != '' else None for x in data]

        if all(x is None for x in data):
            cell = gspread.Cell(row=ticker_rows[ticker], col=col_acoes, value="NAO")
            cells_to_update.append(cell)
        else:
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

            cell = gspread.Cell(row=ticker_rows[ticker], col=col_acoes, value="SIM" if roic_ok and crescente else "NAO")
            cells_to_update.append(cell)

    acoes_sheet.update_cells(cells_to_update)


# def modela_e_verifica_crescente(gc, sheet_id, tickers, campo, col_acoes, col_ticker):
#     acoes_sheet = gc.open_by_key(sheet_id).worksheet('Açoes')
#
#     ticker_rows = {ticker: acoes_sheet.find(ticker).row for ticker in tickers}
#
#     ticker_sheets = []
#     for ticker in tickers:
#         ticker_sheet = gc.open_by_key(sheet_id).worksheet(ticker)
#         ticker_sheets.append(ticker_sheet)
#
#     cells_to_update = []
#
#     for ticker, ticker_sheet in zip(tickers, ticker_sheets):
#         data = ticker_sheet.col_values(col_ticker)[1:12]
#         data = [int(x.replace('.', '')) if x != '' and x != '-' else None for x in data]
#
#         if all(x is None for x in data):
#             cell = gspread.Cell(row=ticker_rows[ticker], col=col_acoes, value="NAO")
#             cells_to_update.append(cell)
#         else:
#             data = [x for x in data if x is not None]
#             data = np.array(data).astype(float)
#
#             model_sarima, model_exp_smoothing = model_receita(data)
#
#             sarima_forecast = model_sarima.forecast(steps=5)
#             exp_smoothing_forecast = model_exp_smoothing.forecast(steps=5)
#
#             crescente_sarima = sarima_forecast[0] > data[-1]
#             crescente_exp_smoothing = exp_smoothing_forecast[0] > data[-1]
#
#             crescente = crescente_sarima or crescente_exp_smoothing
#
#             cell = gspread.Cell(row=ticker_rows[ticker], col=col_acoes, value="SIM" if crescente else "NAO")
#             cells_to_update.append(cell)
#
#     acoes_sheet.update_cells(cells_to_update)


def config_ini():
    sheet_id = '1_pZOasF7mjs-JtibgEusc1Bh80i2IQOcsEW0mCBoEHo'
    gc = conn_sheet()

    # Abre a planilha "Ações" e pega todos os tickers
    acoes_sheet = gc.open_by_key(sheet_id).worksheet('Açoes')
    all_tickers = acoes_sheet.col_values(1)[2:]  # começa da linha 3

    # Verifica se existe um arquivo de tickers processados
    try:
        with open('tickers_processed.json', 'r') as f:
            tickers_processed = json.load(f)
    except FileNotFoundError:
        tickers_processed = []

    # Pega os tickers que ainda não foram processados
    tickers = [ticker for ticker in all_tickers if ticker not in tickers_processed]

    if tickers:
        servico = Service(ChromeDriverManager().install())

        with webdriver.Chrome(service=servico) as navegador:
            # login
            navegador.maximize_window()
            login = login_inv_10(navegador, url="https://investidor10.com.br/")

            if login:
                for ticker in tickers:
                    try:
                        # Abre a guia com o nome do ticker
                        ticker_sheet = gc.open_by_key(sheet_id).worksheet(ticker)

                        # Verifica se a guia já contém dados
                        if not ticker_sheet.get_all_values():
                            # Se não, preenche a guia com os dados
                            preencher_sheets(navegador, [ticker], ticker_sheet)

                        # Adiciona o ticker à lista de tickers processados e salva no arquivo
                        tickers_processed.append(ticker)
                        with open('tickers_processed.json', 'w') as f:
                            json.dump(tickers_processed, f)

                    except Exception as e:
                        print(f"Erro ao processar o ticker {ticker}: {str(e)}")
                        continue

            else:
                navegador.close()
                config_ini()

            print("\nFinalizado")

        # Após todos os tickers serem processados, exclui o arquivo
        # if os.path.exists('tickers_processed.json'):
        #     os.remove('tickers_processed.json')
        # if os.path.exists('tickers_verified.json'):
        #     os.remove('tickers_verified.json')

    else:
        # Verifica se existe um arquivo de tickers verificados
        try:
            with open('tickers_verified.json', 'r') as f:
                tickers_verified = json.load(f)
        except FileNotFoundError:
            tickers_verified = []

        # Pega os tickers que ainda não foram verificados
        tickers_to_verify = [ticker for ticker in all_tickers if ticker not in tickers_verified]
        modela_e_verifica_crescente(gc, sheet_id, tickers_to_verify, 'Receita', 8, 2)
        modela_e_verifica_crescente(gc, sheet_id, tickers_to_verify, 'Lucro Liquido', 9, 5)
        modela_e_verifica_crescente(gc, sheet_id, tickers_to_verify, 'ROIC', 10, 15)

        # for ticker in tickers_to_verify:
        #     # Verifica a receita para cada ticker
        #     verifica_receita_crescente(gc, sheet_id, ticker)
        #
        #     # Adiciona o ticker à lista de tickers verificados e salva no arquivo
        #     tickers_verified.append(ticker)
        #     with open('tickers_verified.json', 'w') as f:
        #         json.dump(tickers_verified, f)


if __name__ == "__main__":
    config_ini()
