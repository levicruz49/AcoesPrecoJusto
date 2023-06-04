from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

servico = Service(ChromeDriverManager().install())
navegador = webdriver.Chrome(service=servico)

def login():
    # url = f'https://investidor10.com.br/acoes/{ticker}/'
    url = f'https://investidor10.com.br/'
    navegador.get(url)

    # Pausar o script até que o usuário pressione Enter.
    input("Pressione Enter após fazer o login: ")
    return True

def busca(ticker):

    new_url = f'https://investidor10.com.br/acoes/{ticker}/'
    navegador.get(new_url)

    # Extrai os dados de lucro líquido aqui
    soup = BeautifulSoup(navegador.page_source, 'html.parser')
    table = soup.find('table', {'id': 'table-balance-results'})
    rows = table.find_all('tr')
    for row in rows:
        columns = row.find_all('th')
        #TODO consegui acessar a tabela, agora precisa fazer o for para procurar o lucro liquido, não como esta abaixo
        if len(columns) > 0 and columns[0].text.strip() == 'Lucro Líquido - (R$)':
            net_income = [column.text.strip() for column in columns[2:]]  # Extrai os lucros a partir da terceira coluna
            return net_income

    return None

if __name__ == "__main__":
    tickers = ['petr4']  # Lista de tickers das empresas desejadas
    acesso = login()

    if acesso:
        for ticker in tickers:
            net_income = busca(ticker)
            if net_income is not None:
                print(f"Net income for {ticker}: {net_income}")
            else:
                print(f"Failed to get net income for {ticker}")

navegador.quit()

