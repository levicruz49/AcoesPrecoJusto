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

    # Cotação do ativo
    cotacao = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[1]/tbody/tr[1]/td[4]/span").text
    cotacao = cotacao.replace(",","")

    # Divida liquida / patrimonio liquido
    if navegador.find_element(By.XPATH,
                              "/html/body/div[1]/div[2]/table[4]/tbody/tr[3]/td[3]/span[2]").text == 'Dív. Líquida':
        div_liq = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[4]/tbody/tr[3]/td[4]/span").text
        patr_liq = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[4]/tbody/tr[4]/td[4]/span").text
        div_liq = div_liq.replace('.', '')
        patr_liq = patr_liq.replace('.', '')

        # Realiza a divisão
        div_liq_patr_liq = round(float(div_liq) / float(patr_liq), 2)
    else:
        div_liq_patr_liq = 0

    # ROA
    if navegador.find_element(By.XPATH,
                              "/html/body/div[1]/div[2]/table[5]/tbody/tr[5]/td[1]/span[2]").text == 'Lucro Líquido':
        lucro_liq = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[5]/tbody/tr[5]/td[2]/span").text
    else:
        lucro_liq = 0

    if navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[4]/tbody/tr[2]/td[1]/span[2]").text == "Ativo":
        ativo = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[4]/tbody/tr[2]/td[2]/span").text
    else:
        ativo = 0

    lucro_liq = lucro_liq.replace(".", "")
    ativo = ativo.replace(".", "")

    # Realiza a divisão
    roa = round((float(lucro_liq) / float(ativo)) * 100,2)

    # Liquidez corrente
    if navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[3]/tbody/tr[10]/td[5]/span[2]").text == 'Liquidez Corr':
        liqu_corrente = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[3]/tbody/tr[10]/td[6]/span").text
    else:
        liqu_corrente = 0

    # P/VP
    if navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[3]/tbody/tr[3]/td[3]/span[2]").text == 'P/VP':
        p_vp = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[3]/tbody/tr[3]/td[4]/span").text
    else:
        p_vp = 0

    # EY -> EBIT / EV
    if navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[5]/tbody/tr[4]/td[1]/span[2]").text == 'EBIT':
        ebit = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[5]/tbody/tr[4]/td[2]/span").text
    else:
        ebit = "-"

    if navegador.find_element(By.XPATH,
                              "/html/body/div[1]/div[2]/table[2]/tbody/tr[2]/td[1]/span[2]").text == 'Valor da firma':
        vl_firma = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[2]/tbody/tr[2]/td[2]/span").text

        if vl_firma == "0" or vl_firma == '-':
            vl_firma = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[2]/tbody/tr[1]/td[2]/span").text # VALOR DE MERCADO
    else:
        vl_firma = 0

    ebit = str(ebit).replace(".", "")
    vl_firma = str(vl_firma).replace(".", "")

    # Faz o calculo no modo padrão do Ebit/Ev
    if ebit == '-':
        if navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[3]/tbody/tr[2]/td[5]/span[2]").text == 'LPA':
            lpa = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/table[3]/tbody/tr[2]/td[6]/span").text
        else:
            lpa = 0

        lpa = lpa.replace(",","")

        # Realiza a divisão
        ey = round(float(lpa) / float(cotacao) * 100, 2)
    else:
    # Realiza a divisão
        ey = round(float(ebit) / float(vl_firma) * 100, 2)

    dados = {
        'div_liq_patr_liq': div_liq_patr_liq,
        'roa': roa,
        'liqu_corrente': liqu_corrente,
        'p_vp': p_vp,
        'ey' : ey
    }

    return dados

if __name__ == "__main__":
    sheet_id = '1_pZOasF7mjs-JtibgEusc1Bh80i2IQOcsEW0mCBoEHo'
    sheet_name = 'dados_empresas'
    gc = conn_sheet()
    sheet = gc.open_by_key(sheet_id).worksheet(sheet_name)

    # Pega todos os tickers da planilha
    all_values = sheet.get_all_values()
    tickers = [row[0] for row in all_values[1:]]

    # Pega a primeira linha vazia, o que não é mais necessario
    start_update_row = next((i for i, row in enumerate(all_values[1:], start=1)), None)

    servico = Service(ChromeDriverManager().install())
    navegador = webdriver.Chrome(service=servico)

    for ticker in tickers:
        url = f"https://www.fundamentus.com.br/detalhes.php?papel={ticker}"
        navegador.get(url)
        dados = get_dados_fundamentalistas_selenium(navegador)

        # Atualiza as colunas C-E com os valores dos dados
        cells = sheet.range(f'B{start_update_row + 1}:F{start_update_row + 1}')
        for j, cell in enumerate(cells):
            if j == 0:
                cell.value = str(dados['div_liq_patr_liq']).replace('.', ',')
            elif j == 1:
                cell.value = str(dados['roa']).replace('.', ',')
            elif j == 2:
                cell.value = str(dados['liqu_corrente']).replace('.', ',')
            elif j == 3:
                cell.value = str(dados['p_vp']).replace('.', ',')
            elif j == 4:
                cell.value = str(dados['ey']).replace('.', ',')
        sheet.update_cells(cells)
        start_update_row += 1
