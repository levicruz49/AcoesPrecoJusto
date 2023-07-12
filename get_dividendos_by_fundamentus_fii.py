from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import pandas as pd
from google.oauth2 import service_account
import gspread


# Estabelece a conexão com a planilha do Google
def conn_sheet():
    KEY_FILE = '/JSONS/acoessempre-2a81866e7af2.json'
    SHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    credentials = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SHEET_SCOPES)

    return gspread.authorize(credentials)


def get_proventos_selenium(navegador):
    # Deixa o tempo para a página recarregar
    time.sleep(2)

    # Obter a tabela de proventos
    soup = BeautifulSoup(navegador.page_source, 'html.parser')
    table = soup.find('table', {'id': 'resultado'})
    proventos = []

    if table:
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            # Pega a data de pagamento e o valor do dividendo
            data_pagamento = cols[2].text
            valor = cols[3].text
            # Converte a data para o ano e o valor para float
            ano = int(data_pagamento.split('/')[-1])
            valor = float(valor.replace(',', '.'))
            proventos.append((ano, valor))
    else:
        print(f'Não foi possível encontrar a tabela de proventos para o papel {ticker}.')

    return proventos


def get_p_vp(navegador):
    p_vp = navegador.find_element(By.XPATH, '/html/body/div[1]/div[2]/table[3]/tbody/tr[4]/td[4]/span').text
    return p_vp


if __name__ == "__main__":
    sheet_id = '1_pZOasF7mjs-JtibgEusc1Bh80i2IQOcsEW0mCBoEHo'
    sheet_name = 'FII'
    gc = conn_sheet()
    sheet = gc.open_by_key(sheet_id).worksheet(sheet_name)

    # Pega todos os tickers da planilha que não têm dados na coluna C  < hoje nao utilizado mais, pega todas as linhas
    all_values = sheet.get_all_values()
    tickers = [row[0] for row in all_values[2:]]

    # Encontra a primeira linha vazia na coluna C < hoje nao utilizado mais, pega todas as linhas
    start_update_row = next((i for i, row in enumerate(all_values[2:], start=2)), None)
    start_update_row_p_vp = next((i for i, row in enumerate(all_values[2:], start=2)), None)

    servico = Service(ChromeDriverManager().install())
    navegador = webdriver.Chrome(service=servico)

    qtd_tickers = 0

    for i in range(2):
        if i < 1:
            for ticker in tickers:
                    url = f"https://www.fundamentus.com.br/fii_proventos.php?papel={ticker}&tipo=2"
                    navegador.get(url)

                    if navegador.find_elements(By.ID, "resultado"):
                        proventos = get_proventos_selenium(navegador)

                        # Organiza os proventos por ano
                        proventos_por_ano = {}
                        for ano, valor in proventos:
                            if ano not in proventos_por_ano:
                                proventos_por_ano[ano] = 0
                            proventos_por_ano[ano] += valor

                        # Obter os proventos para os períodos solicitados
                        ano_corrente = int(time.strftime("%Y"))
                        proventos_1y = proventos_por_ano.get(ano_corrente - 1, 0)
                        proventos_6y = sum(
                            proventos_por_ano.get(ano, 0) for ano in range((ano_corrente - 1) - 6, ano_corrente)) / 6
                        # proventos_max = sum(proventos_por_ano.values())

                        # Atualiza as colunas C-E com os proventos
                        cells = sheet.range(f'C{start_update_row + 1}:E{start_update_row + 1}')
                        for j, cell in enumerate(cells):
                            if j == 0:
                                cell.value = str(proventos_1y).replace('.', ',')
                            elif j == 1:
                                cell.value = str(proventos_6y).replace('.', ',')
                            # elif j == 2:
                            #     cell.value = str(proventos_max).replace('.', ',')
                        sheet.update_cells(cells)

                        start_update_row += 1

                    else:
                        cells = sheet.range(f'C{start_update_row + 1}:E{start_update_row + 1}')
                        for j, cell in enumerate(cells):
                            if j == 0:
                                cell.value = str(0).replace('.', ',')
                            elif j == 1:
                                cell.value = str(0).replace('.', ',')
                            # elif j == 2:
                            #     cell.value = str(proventos_max).replace('.', ',')
                        sheet.update_cells(cells)

                        start_update_row += 1
            i += 1
        else:
            for ticker in tickers:
                url = f"https://www.fundamentus.com.br/detalhes.php?papel={ticker}"
                navegador.get(url)

                if navegador.find_elements(By.XPATH,
                                          "/html/body/div[1]/div[2]/table[3]/tbody/tr[4]/td[3]/span[2]"):
                    p_vp = get_p_vp(navegador)

                    # Atualiza as colunas C-E com os proventos
                    cells = sheet.range(f'C{start_update_row_p_vp + 1}:E{start_update_row_p_vp + 1}')
                    for j, cell in enumerate(cells):
                        if j == 2:
                            cell.value = str(p_vp).replace('.', ',')
                    sheet.update_cells(cells)

                    start_update_row_p_vp += 1
                else:
                    cells = sheet.range(f'C{start_update_row_p_vp + 1}:E{start_update_row_p_vp + 1}')
                    for j, cell in enumerate(cells):
                        if j == 2:
                            cell.value = str(0).replace('.', ',')
                    sheet.update_cells(cells)

                    start_update_row_p_vp += 1
                    i+=1

    navegador.quit()