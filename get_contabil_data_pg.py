import json
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from facade import get_tickers, insere_pg, get_tickers_inv_10, insere_pg_inv10, atualiza_pg_inv10


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
    descer_tela_1 = None
    descer_tela_2 = None

    # pegar os dados da primeira tabela
    xpaths_descer_tela_1 = ["/html/body/div[2]/div/main/section/div/div[4]/header/div/ul/li[3]/a"]
    for path in xpaths_descer_tela_1:
        try:
            time.sleep(1)
            descer_tela_1 = WebDriverWait(navegador, 1).until(EC.presence_of_element_located((By.XPATH, path)))
            navegador.execute_script("arguments[0].scrollIntoView({block: 'center'});", descer_tela_1)
            time.sleep(2)
            break
        except Exception as e:
            pass

    if not descer_tela_1:
        print("Falha ao encontrar algum path para descer a tela. 1")

    # seleciona 10 anos e expande tabela
    try:
        navegador.find_element(By.XPATH, "/html/body/div[2]/div/main/section/div/div[4]/header/div/ul/li[3]/a").click()
        time.sleep(1)
        navegador.execute_script("arguments[0].scrollIntoView({block: 'center'});", WebDriverWait(navegador, 1).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/main/section/div/div[4]/button"))))
        time.sleep(2)
        navegador.find_element(By.XPATH, "/html/body/div[2]/div/main/section/div/div[4]/button").click()
    except:
        navegador.find_element(By.XPATH, "/html/body/div[2]/div/main/section/div/div[4]/header/div/ul/li[3]/a").click()
        time.sleep(1)
        navegador.execute_script("arguments[0].scrollIntoView({block: 'center'});", WebDriverWait(navegador, 1).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/main/section/div/div[4]/button"))))
        time.sleep(2)
        navegador.find_element(By.XPATH, "/html/body/div[2]/div/main/section/div/div[4]/button").click()

    # Localiza a tabela pelo id
    table_1 = navegador.find_element(By.ID, 'table-indicators-history')

    # Encontra as linhas da tabela
    rows = table_1.find_elements(By.TAG_NAME, 'tr')

    # Encontra os cabeçalhos da tabela (ano)
    header_row = rows[0]
    header_cells = header_row.find_elements(By.TAG_NAME, 'th')
    years = [cell.text for cell in header_cells if cell.text.isdigit()]  # Somente números serão considerados anos

    # Ignora a primeira linha que são os cabeçalhos
    data_rows = rows[1:]

    data_1 = {}
    for year in years:
        data_1[year] = []

    for row in data_rows:
        cells = row.find_elements(By.TAG_NAME, 'td')
        indicator_name = cells[0].text
        cell_values = [cell.text for cell in cells[2:] if cell.text != '']

        for i, year in enumerate(years):
            # Ignora células sem texto e formata as restantes
            if i < len(cell_values) and cell_values[i]:
                value = cell_values[i].replace('R$', '').replace(' Bilhões', '').replace('%', '').strip()

                # Se tem parênteses, o número é negativo
                if '(' in value and ')' in value:
                    value = value.replace('(', '').replace(')', '')
                    if value:
                        # Se ainda tem valor após remover os parênteses, é um número negativo
                        value = '-' + value
                elif '-' in value and value.index('-') == len(value) - 1:  # '-' está no final, trate como None
                    value = None
                cell_values[i] = value
                data_1[year].append({indicator_name: cell_values[i]})

    # PEGA O EV = VALOR DE FIRMA
    xpaths_descer_tela_ev = [
        "/html/body/div[2]/div/main/section/div/div[12]/div[4]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[11]/div[4]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]"]

    for xpath in xpaths_descer_tela_ev:
        try:
            time.sleep(1)
            descer_tela_1 = WebDriverWait(navegador, 1).until(EC.presence_of_element_located((By.XPATH, xpath)))
            navegador.execute_script("arguments[0].scrollIntoView({block: 'center'});", descer_tela_1)
            time.sleep(2)
            break
        except Exception as e:
            pass

    # seleciona valores detalhados e pega os valores
    try:
        navegador.find_element(By.XPATH,
                               "/html/body/div[2]/div/main/section/div/div[12]/div[4]/div[1]/div/ul/li[2]/span/span[1]/span").click()
        navegador.find_element(By.XPATH, "/html/body/span/span/span[2]/ul/li[2]").click()
        time.sleep(1)
        valor_firma = navegador.find_element(By.XPATH,
                                             "/html/body/div[2]/div/main/section/div/div[12]/div[4]/div[2]/div/div[2]/span[2]/div[2]").text
        valor_mercado = navegador.find_element(By.XPATH,
                                               "/html/body/div[2]/div/main/section/div/div[12]/div[4]/div[2]/div/div[1]/span[2]/div[2]").text
    except:
        navegador.find_element(By.XPATH,
                               "/html/body/div[2]/div/main/section/div/div[11]/div[4]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]").click()
        navegador.find_element(By.XPATH, "/html/body/span/span/span[2]/ul/li[2]").click()
        time.sleep(1)
        valor_firma = navegador.find_element(By.XPATH,
                                             "/html/body/div[2]/div/main/section/div/div[11]/div[4]/div[2]/div/div[2]/span[2]/div[2]").text
        valor_mercado = navegador.find_element(By.XPATH,
                                               "/html/body/div[2]/div/main/section/div/div[11]/div[4]/div[2]/div/div[1]/span[2]/div[2]").text

    valor_firma = valor_firma.replace('R$', '').replace(' Bilhões', '').replace('%', '').strip()
    valor_mercado = valor_mercado.replace('R$', '').replace(' Bilhões', '').replace('%', '').strip()

    # VAI PARA A TABELA 2

    xpaths_descer_tela_2 = ["/html/body/div[2]/div/main/section/div/div[14]/div[2]",
                            "/html/body/div[2]/div/main/section/div/div[13]/div[2]",
                            "/html/body/div[2]/div/main/section/div/div[12]/div[2]/div[1]",
                            "/html/body/div[2]/div/main/section/div/div[12]/div[3]",
                            ]

    for path in xpaths_descer_tela_2:
        try:
            time.sleep(1)
            descer_tela = WebDriverWait(navegador, 1).until(EC.presence_of_element_located((By.XPATH, path)))
            navegador.execute_script("arguments[0].scrollIntoView({block: 'center'});", descer_tela)
            break
        except Exception as e:
            pass

    if not descer_tela_2:
        print("Falha ao encontrar algum path para descer a tela. 2")

    time.sleep(3)

    xpaths_menu_anos = [
        "/html/body/div[2]/div/main/section/div/div[14]/div[3]/div[1]/div/ul/li[5]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[14]/div[2]/div[1]/div/ul/li[5]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[13]/div[2]/div[1]/div/ul/li[5]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[12]/div[3]/div[1]/div/ul/li[5]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[12]/div[2]/div[1]/div/ul/li[5]/span/span[1]/span/span[1]"
    ]

    for path in xpaths_menu_anos:
        try:
            menu_anos = WebDriverWait(navegador, 1).until(EC.presence_of_element_located((By.XPATH, path)))
            time.sleep(1)
            menu_anos.click()
            break
        except Exception as e:
            pass

    # Seleciona 15 ANOS ou 10 ANOS
    try:
        elemento_ano = navegador.find_element(By.XPATH, '/html/body/span/span/span[2]/ul/li[5]')
    except:
        elemento_ano = navegador.find_element(By.XPATH, '/html/body/span/span/span[2]/ul/li[4]')

    elemento_ano.click()
    time.sleep(1)

    xpaths_val_detalhados = [
        "/html/body/div[2]/div/main/section/div/div[14]/div[3]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[14]/div[2]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[13]/div[2]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[12]/div[3]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]",
        "/html/body/div[2]/div/main/section/div/div[12]/div[2]/div[1]/div/ul/li[2]/span/span[1]/span/span[1]"
    ]

    for path in xpaths_val_detalhados:
        try:
            val_detalhados = WebDriverWait(navegador, 1).until(EC.presence_of_element_located((By.XPATH, path)))
            time.sleep(1)
            val_detalhados.click()
            break
        except Exception as e:
            pass

    # Seleciona os valores como detalhados
    navegador.find_element(By.XPATH, "/html/body/span/span/span[2]/ul/li[2]").click()

    # Localiza a tabela pelo id
    table = navegador.find_element(By.ID, 'table-balance-results')

    # Encontra as linhas da tabela
    rows = table.find_elements(By.TAG_NAME, 'tr')

    # Encontra os cabeçalhos da tabela (ano)
    header_row = rows[0]
    header_cells = header_row.find_elements(By.TAG_NAME, 'th')
    years = [cell.text for cell in header_cells if cell.text.isdigit()]  # Somente números serão considerados anos

    # Ignora a primeira linha que são os cabeçalhos
    data_rows = rows[1:]

    data_2 = {}
    for year in years:
        data_2[year] = []

    for row in data_rows:
        cells = row.find_elements(By.TAG_NAME, 'td')
        indicator_name_2 = cells[0].text
        cell_values = [cell.text for cell in cells[2:] if cell.text != '']

        for i, year in enumerate(years):
            # Ignora células sem texto e formata as restantes
            if i < len(cell_values) and cell_values[i]:
                value = cell_values[i].replace('R$', '').replace(' Bilhões', '').replace('%', '').strip()

                # Se tem parênteses, o número é negativo
                if '(' in value and ')' in value:
                    value = value.replace('(', '').replace(')', '')
                    if value:
                        # Se ainda tem valor após remover os parênteses, é um número negativo
                        value = '-' + value
                elif '-' in value and value.index('-') == len(value) - 1:  # '-' está no final, trate como None
                    value = None
                cell_values[i] = value
                data_2[year].append({indicator_name_2: cell_values[i]})

    return data_1, data_2, valor_firma


# Função para converter a escala de milhões para a escala correta
def convert_scale(value):
    value = value.replace('.', '').replace(',', '.')  # Remova o ponto antes de converter para int
    if isinstance(value, str):
        value = float(value)  # Primeiro converte para float
    value = int(value)  # Depois converte para int
    return value * 1000000


# Função para identificar os anos no cabeçalho
def identify_years(header_cells):
    years = []
    for cell in header_cells:
        text = cell.text
        if text.isdigit():
            years.append(text)
        elif text.startswith('12/'):
            years.append(text.split('/')[1])
    return years


def get_dados_fundamentalistas_selenium_fundamentus(navegador, ticket):
    navegador.get(f"https://fundamentei.com/br/{ticket}")

    time.sleep(1)

    descer_tela = navegador.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[3]/div[14]")
    navegador.execute_script("arguments[0].scrollIntoView(true);", descer_tela)

    xpaths_tabela = ["/html/body/div[1]/div[2]/div[3]/div[12]/div/table",
                     "/html/body/div[1]/div[2]/div[3]/div[13]/div/table",
                     "/html/body/div[1]/div[2]/div[3]/div[14]/div/table"]

    table = None

    for path in xpaths_tabela:
        try:
            time.sleep(1)
            table = WebDriverWait(navegador, 1).until(EC.presence_of_element_located((By.XPATH, path)))
            break
        except Exception as e:
            print(f"Failed to find element with xpath {path}. Error: {e}")

    # Encontra as linhas de dados da tabela
    data_rows = table.find_elements(By.TAG_NAME, 'tr')[1:]  # Ignora a primeira linha que são os cabeçalhos

    # Encontra os anos nas primeiras células de cada linha
    header_cells = [row.find_elements(By.TAG_NAME, 'td')[0] for row in data_rows]
    years = identify_years(header_cells)  # Usa a função para identificar os anos corretos

    header_rows = table.find_elements(By.TAG_NAME, 'thead')[0]

    header_cells = [cell.text for cell in header_rows.find_elements(By.TAG_NAME, 'th')]

    data = {year: {} for year in years}

    fields_of_interest_map = {
        'Patrimônio Líquido': ['Patrimônio Líquido', 'Pat. Líq.'],
        'Receita Inter. Fin.': ['Receita Inter. Fin.', 'Receita Líq.'],
        'Lucro Líquido': ['Lucro Líquido', 'Lucro Líq.'],
        'Margem Líquida': ['Margem Líquida', 'Mrg. Líq.'],
        'ROE': ['ROE'],
        'Payout': ['Payout'],
        'EBITDA': ['EBITDA'],
        'EBIT': ['EBIT'],
        'Impostos': ['Impostos'],
        'Dívida': ['Dívida']
    }

    for year, row in zip(years, data_rows):
        cells = row.find_elements(By.TAG_NAME, 'td')

        for field in fields_of_interest_map:
            for variant in fields_of_interest_map[field]:
                if variant in header_cells:
                    cell = cells[header_cells.index(variant)]  # removido o +1
                    value = cell.text.replace('R$', '').replace('%', '').strip()
                    if value == '-':
                        value = None
                    elif value.startswith('(') and value.endswith(')'):
                        value = -float(value[1:-1])
                    elif value and field not in ['Margem Líquida', 'ROE', 'Payout']:
                        value = convert_scale(value)
                    data[year][field] = value
                    break

    return data


def config_ini():
    all_tickers = get_tickers()
    all_tickers_inv_10 = get_tickers_inv_10()

    # Verifica se existe um arquivo de tickers processados
    try:
        with open('JSONS/tickers_processed.json', 'r') as f:
            tickers_processed = json.load(f)
    except FileNotFoundError:
        tickers_processed = []

    # Pega os tickers que ainda não foram processados
    tickers = [ticker for ticker in all_tickers if ticker not in tickers_processed]
    tickers_10 = [ticker_10 for ticker_10 in all_tickers_inv_10]

    if tickers:
        chrome_options = Options()
        chrome_options.add_argument("--user-data-dir=C:\\Users\\mrcr\\AppData\\Local\\Google\\Chrome\\User Data")
        servico = Service(ChromeDriverManager().install())

        with webdriver.Chrome(service=servico, options=chrome_options) as navegador:

            for ticker in tickers:
                dados = get_dados_fundamentalistas_selenium_fundamentus(navegador, ticker)
                insere_pg(dados, ticker)

                # Adiciona o ticker à lista de tickers processados e salva no arquivo
                tickers_processed.append(ticker)
                with open('JSONS/tickers_processed.json', 'w') as f:
                    json.dump(tickers_processed, f)

            navegador.close()
            print("\nFinalizado")

    elif tickers_10:
        chrome_options = Options()
        chrome_options.add_argument("--user-data-dir=C:\\Users\\mrcr\\AppData\\Local\\Google\\Chrome\\User Data")
        servico = Service(ChromeDriverManager().install())

        with webdriver.Chrome(service=servico, options=chrome_options) as navegador:

            for ticker in tickers_10:
                url = f"https://investidor10.com.br/acoes/{ticker}"
                navegador.get(url)

                if login(navegador):
                    dados = get_dados_fundamentalistas_selenium_inv_10(navegador)
                    atualiza_pg_inv10(dados, ticker)

            navegador.close()
            print("\nFinalizado")
