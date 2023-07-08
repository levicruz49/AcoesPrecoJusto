import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
import json

from cotacao_acao import config_ini_cotacao
from facade import get_tickers, conexao_pg


def get_proventos_selenium(navegador, ticker):
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


def config_ini():
    all_tickers = get_tickers()

    # Verifica se existe um arquivo de tickers processados
    try:
        with open('tickers_processed_dividends.json', 'r') as f:
            tickers_processed = json.load(f)
    except FileNotFoundError:
        tickers_processed = []

    # Pega os tickers que ainda não foram processados
    tickers = [ticker for ticker in all_tickers if ticker not in tickers_processed]

    if tickers:
        servico = Service(ChromeDriverManager().install())

        with webdriver.Chrome(service=servico) as navegador:
            for ticker in tickers:
                url = f"https://www.fundamentus.com.br/proventos.php?papel={ticker}&tipo=2"
                navegador.get(url)

                proventos = get_proventos_selenium(navegador, ticker)

                # Obter os proventos para os períodos solicitados
                proventos_1y = round(sum([float(p[1].replace(',', '.')) if len(p) > 1 else 0 for p in proventos if
                                          int(p[0]) == (int(time.strftime("%Y")) - 1)]), 2)
                proventos_6y = round(sum([float(p[1].replace(',', '.')) if len(p) > 1 else 0 for p in proventos if
                                          int(p[0]) >= (int(time.strftime("%Y")) - 1) - 6 and int(p[0]) != int(
                                              time.strftime("%Y"))]) / 6, 2)
                proventos_max = round(sum([float(p[1].replace(',', '.')) if len(p) > 1 else 0 for p in proventos]), 2)

                # Abrindo a conexão com o PostgreSQL
                conn = conexao_pg()
                cur = conn.cursor()

                # Atualizando a tabela
                update_query = """
                                    UPDATE Acoes 
                                    SET div_12_meses = %s, med_div_6_anos = %s, maximo_div = %s
                                    WHERE ticker = %s
                                    """
                cur.execute(update_query, (proventos_1y, proventos_6y, proventos_max, ticker))

                # Fechando a conexão
                conn.commit()
                cur.close()
                conn.close()

                # Atualizando a lista de tickers processados
                tickers_processed.append(ticker)
                with open('tickers_processed_dividends.json', 'w') as f:
                    json.dump(tickers_processed, f)


if __name__ == "__main__":
    config_ini_cotacao()
    config_ini()
