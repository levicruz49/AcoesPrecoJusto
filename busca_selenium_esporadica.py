import json
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from facade import atualiza_pg_inv10, atualiza_ev_inv10


def login(navegador):
    img = WebDriverWait(navegador, 10).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/header/div[1]/div/div[2]/div/span/a/img")))

    alt = img.get_attribute('alt')

    if alt == 'Levi Cruz':
        return True

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

    try:
        img = WebDriverWait(navegador, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/header/div[1]/div/div[2]/div/span/a/img")))

        alt = img.get_attribute('alt')

        if alt == 'Levi Cruz':
            return True
        else:
            return False
    except:
        # SE DER ERRO AO ENTRAR FAZ O LOGIN NOVAMENTE

        time.sleep(2)
        navegador.find_element(By.XPATH, "/html/body/div[4]/div/button").click()

        # Click em entrar
        entrar = WebDriverWait(navegador, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[3]/header/div[1]/div/div[2]/nav/ul/li[2]/a")))

        time.sleep(2)

        entrar.click()

        # Fazer Login
        navegador.find_element(By.XPATH, "/html/body/div[4]/div/div[1]/form/div[1]/input").send_keys(
            "levicruz49@gmail.com")
        navegador.find_element(By.XPATH, "/html/body/div[4]/div/div[1]/form/div[2]/input").send_keys("Embraer198@")

        # Entrar
        navegador.find_element(By.XPATH, "/html/body/div[4]/div/div[1]/form/div[3]/input").click()


def get_dados_fundamentalistas_selenium_inv_10(navegador):
    # Deixa o tempo para a página recarregar
    time.sleep(3)

    # pegar os dados da primeira tabela
    xpaths_descer_tela = ["/html/body/div[2]/div/main/section/div/div[12]/div[4]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]",
                          "/html/body/div[2]/div/main/section/div/div[11]/div[4]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]"]
    for xpath in xpaths_descer_tela:
        try:
            time.sleep(1)
            descer_tela_1 = WebDriverWait(navegador, 1).until(EC.presence_of_element_located((By.XPATH, xpath)))
            navegador.execute_script("arguments[0].scrollIntoView({block: 'center'});", descer_tela_1)
            time.sleep(2)
            break
        except Exception as e:
            pass

    # seleciona 10 anos e expande tabela
    try:
        navegador.find_element(By.XPATH, "/html/body/div[2]/div/main/section/div/div[12]/div[4]/div[1]/div/ul/li[2]/span/span[1]/span").click()
        navegador.find_element(By.XPATH, "/html/body/span/span/span[2]/ul/li[2]").click()
        time.sleep(1)
        valor_firma = navegador.find_element(By.XPATH,
                                             "/html/body/div[2]/div/main/section/div/div[12]/div[4]/div[2]/div/div[2]/span[2]/div[2]").text
        valor_mercado = navegador.find_element(By.XPATH,
                                               "/html/body/div[2]/div/main/section/div/div[12]/div[4]/div[2]/div/div[1]/span[2]/div[2]").text
    except:
        navegador.find_element(By.XPATH, "/html/body/div[2]/div/main/section/div/div[11]/div[4]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]").click()
        navegador.find_element(By.XPATH, "/html/body/span/span/span[2]/ul/li[2]").click()
        time.sleep(1)
        valor_firma = navegador.find_element(By.XPATH,
                                             "/html/body/div[2]/div/main/section/div/div[11]/div[4]/div[2]/div/div[2]/span[2]/div[2]").text
        valor_mercado = navegador.find_element(By.XPATH,
                                               "/html/body/div[2]/div/main/section/div/div[11]/div[4]/div[2]/div/div[1]/span[2]/div[2]").text

    valor_firma = valor_firma.replace('R$', '').replace(' Bilhões', '').replace('%', '').strip()
    valor_mercado =valor_mercado.replace('R$', '').replace(' Bilhões', '').replace('%', '').strip()

    return valor_firma


def config_ini():
    # Pega os tickers que ainda não foram processados
    tickers_10 = ["TASA3","RADL3","RANI3","ABCB4","CXSE3","BBAS3","AESB3"]

    chrome_options = Options()
    chrome_options.add_argument("--user-data-dir=C:\\Users\\mrcr\\AppData\\Local\\Google\\Chrome\\User Data")
    servico = Service(ChromeDriverManager().install())

    with webdriver.Chrome(service=servico, options=chrome_options) as navegador:

        for ticker in tickers_10:
            url = f"https://investidor10.com.br/acoes/{ticker}"
            navegador.get(url)

            if login(navegador):
                dados = get_dados_fundamentalistas_selenium_inv_10(navegador)
                atualiza_ev_inv10(dados, ticker)

        navegador.close()
        print("\nFinalizado")


if __name__ == "__main__":
    config_ini()
