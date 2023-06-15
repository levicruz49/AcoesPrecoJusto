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


def get_proventos_selenium(navegador):

    # Marca o checkbox "chbAgruparAno"
    WebDriverWait(navegador, 10).until(EC.presence_of_element_located((By.ID, "chbAgruparAno"))).click()

    # Deixa o tempo para a página recarregar
    time.sleep(2)

    # Obter a tabela de proventos
    soup = BeautifulSoup(navegador.page_source, 'html.parser')
    table = soup.find('table', {'id': 'resultado-anual'})
    proventos = []

    if table:
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            proventos.append([col.text for col in cols])
    else:
        print(f'Não foi possível encontrar a tabela de proventos para o papel {ticker}.')

    return proventos


if __name__ == "__main__":
    sheet_id = '1_pZOasF7mjs-JtibgEusc1Bh80i2IQOcsEW0mCBoEHo'
    sheet_name = 'Açoes'
    gc = conn_sheet()
    sheet = gc.open_by_key(sheet_id).worksheet(sheet_name)

    # Pega todos os tickers da planilha que não têm dados nas colunas C, D e E
    all_values = sheet.get_all_values()
    tickers = [row[0] for row in all_values[1:] if not (row[2] and row[3] and row[4])]

    # Encontra a primeira linha vazia nas colunas C, D e E
    start_update_row = next((i for i, row in enumerate(all_values[2:], start=2) if not (row[2] and row[3] and row[4])),
                            None)

    servico = Service(ChromeDriverManager().install())
    navegador = webdriver.Chrome(service=servico)

    for ticker in tickers:
        url = f"https://www.fundamentus.com.br/proventos.php?papel={ticker}&tipo=2"
        navegador.get(url)

        proventos = get_proventos_selenium(navegador)

        # Obter os proventos para os períodos solicitados
        proventos_1y = sum([float(p[1].replace(',', '.')) if len(p) > 1 else 0 for p in proventos if int(p[0]) == (int(time.strftime("%Y"))-1)])
        proventos_6y = sum([float(p[1].replace(',', '.')) if len(p) > 1 else 0 for p in proventos if
                            int(p[0]) >= (int(time.strftime("%Y"))-1) - 6 and int(p[0]) != int(time.strftime("%Y"))]) / 6
        # proventos_6y = sum([float(p[1].replace(',', '.')) if len(p) > 1 else 0 for p in proventos if int(p[0]) >= int(time.strftime("%Y")) - 5])
        proventos_max = sum([float(p[1].replace(',', '.')) if len(p) > 1 else 0 for p in proventos])

        # Atualiza as colunas C-E com os proventos
        cells = sheet.range(f'C{start_update_row + 1}:E{start_update_row + 1}')
        for j, cell in enumerate(cells):
            if j == 0:
                cell.value = str(proventos_1y).replace('.', ',')
            elif j == 1:
                cell.value = str(proventos_6y).replace('.', ',')
            elif j == 2:
                cell.value = str(proventos_max).replace('.', ',')
        sheet.update_cells(cells)

        start_update_row += 1
