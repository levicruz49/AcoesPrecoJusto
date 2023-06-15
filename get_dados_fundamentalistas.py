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
    KEY_FILE = 'C:\\Users\\mrcr\\Documents\\projetos_python\\AcoesPrecoJusto\\acoessempre-2a81866e7af2.json'
    SHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    credentials = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SHEET_SCOPES)

    return gspread.authorize(credentials)


def get_dados_fundamentalistas_selenium(navegador):

   # Deixa o tempo para a página recarregar
    time.sleep(2)

    if navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[4]/tbody/tr[3]/td[3]/span[2]").text == 'Dív. Líquida':
        div_liq = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[4]/tbody/tr[3]/td[4]/span").text
        patr_liq = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[4]/tbody/tr[4]/td[4]/span").text
        div_liq = div_liq.replace('.', '')
        patr_liq = patr_liq.replace('.', '')

        # Realiza a divisão
        div_liq_patr_liq = round(float(div_liq) / float(patr_liq),2)
    else:
        div_liq_patr_liq = 0

    return div_liq_patr_liq


if __name__ == "__main__":
    sheet_id = '1_pZOasF7mjs-JtibgEusc1Bh80i2IQOcsEW0mCBoEHo'
    sheet_name = 'dados_empresas'
    gc = conn_sheet()
    sheet = gc.open_by_key(sheet_id).worksheet(sheet_name)

    # Pega todos os tickers da planilha que não têm dados na coluna C
    all_values = sheet.get_all_values()
    tickers = [row[0] for row in all_values[1:] if not row[1]]

    # Encontra a primeira linha vazia na coluna B
    start_update_row = next((i for i, row in enumerate(all_values[1:], start=1) if not row[1]), None)

    servico = Service(ChromeDriverManager().install())
    navegador = webdriver.Chrome(service=servico)

    for ticker in tickers:
        url = f"https://www.fundamentus.com.br/detalhes.php?papel={ticker}"
        navegador.get(url)
        dados = get_dados_fundamentalistas_selenium(navegador)

        # Atualiza as colunas C-E com os proventos
        cells = sheet.range(f'B{start_update_row + 1}:E{start_update_row + 1}')
        for j, cell in enumerate(cells):
            if j == 0:
                cell.value = str(dados).replace('.', ',')
            # elif j == 1:
            #     cell.value = str(dados).replace('.', ',')
            # elif j == 2:
            #     cell.value = str(proventos_max).replace('.', ',')
        sheet.update_cells(cells)
        start_update_row += 1
