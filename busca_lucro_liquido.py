from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

servico = Service(ChromeDriverManager().install())
navegador = webdriver.Chrome(service=servico)

def get_net_income(ticker):
    url = f'https://investidor10.com.br/acoes/{ticker}/'
    navegador.get(url)
    WebDriverWait(navegador, 10).until(EC.presence_of_element_located((By.ID, "table-balance-results")))
    # Aguarda até que a tabela com o ID "table-balance-results" esteja presente na página

    # Extrai os dados de lucro líquido aqui
    soup = BeautifulSoup(navegador.page_source, 'html.parser')
    table = soup.find('table', {'id': 'table-balance-results'})
    rows = table.find_all('tr')
    for row in rows:
        columns = row.find_all('td')
        if len(columns) > 0 and columns[0].text.strip() == 'Lucro Líquido - (R$)':
            net_income = [column.text.strip() for column in columns[2:]]  # Extrai os lucros a partir da terceira coluna
            return net_income

    return None

if __name__ == "__main__":
    tickers = ['petr4']  # Lista de tickers das empresas desejadas

    for ticker in tickers:
        net_income = get_net_income(ticker)
        if net_income is not None:
            print(f"Net income for {ticker}: {net_income}")
        else:
            print(f"Failed to get net income for {ticker}")

navegador.quit()

