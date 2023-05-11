from google.oauth2 import service_account
from googleapiclient.discovery import build
import yfinance as yf
import requests
import pandas as pd
import gspread
import asyncio
import aiohttp
import time


def conn_sheet():
    KEY_FILE = 'C:\\Users\\mrcr\\Documents\\projetos_python\\AcoesPrecoJusto\\acoessempre-2a81866e7af2.json'
    SHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    credentials = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SHEET_SCOPES)

    return gspread.authorize(credentials)


def save_df_to_sheet(df, sheet_name, sheet_id):
    gc = conn_sheet()
    sheet = gc.open_by_key(sheet_id).worksheet(sheet_name)

    # Limpar o conteúdo da planilha
    sheet.clear()

    # Atualizar o cabeçalho da planilha
    header = list(df.columns)
    sheet.append_row(header)

    # Atualizar os dados da planilha
    data = df.applymap(lambda x: str(x) if isinstance(x, float) else x).values.tolist()  # Converter o DataFrame em uma lista de listas
    cell_range = f'A2:{gspread.utils.rowcol_to_a1(len(data) + 1, len(header))}'
    cells = sheet.range(cell_range)
    for i, row in enumerate(data):
        for j, cell in enumerate(row):
            cells[i * len(header) + j].value = cell
    sheet.update_cells(cells)  # Atualizar todas as células de uma só vez


def get_all_tickers():
    url = "http://www.fundamentus.com.br/resultado.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    # Encontrar todos os tickers na página
    tickers = set()
    lines = response.text.splitlines()
    for line in lines:
        if '<a href="detalhes.php?papel=' in line:
            ticker = line.split('="detalhes.php?papel=')[1].split('">')[0]
            tickers.add(ticker)

    return sorted(tickers)


def get_all_fii_tickers():
    url = "https://www.fundsexplorer.com.br/ranking"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    # Encontrar todos os tickers na página
    fii_tickers = set()
    lines = response.text.splitlines()
    for line in lines:
        if '<a href="/funds/' in line:
            fii_ticker = line.split('="/funds/')[1].split('">')[0]
            fii_tickers.add(fii_ticker)

    return sorted(fii_tickers)


def save_tickers_to_csv(tickers, filename="tickers.csv"):
    tickers_df = pd.DataFrame(tickers, columns=["Ticker"])
    tickers_df.to_csv(filename, index=False)


def read_tickers_from_csv(filename="tickers.csv"):
    tickers_df = pd.read_csv(filename)
    return tickers_df["Ticker"].tolist()


def add_suffix_to_tickers(tickers, suffix=".SA"):
    return [ticker + suffix for ticker in tickers]


async def fetch_stock_info(session, url, ticker):
    async with session.get(url) as response:
        if response.status == 200:
            data = await response.json()
            result = data["quoteSummary"]["result"]
            if not result:
                print(f"Não foi possível encontrar dados para o ticker {ticker}")
                return None

            quote_data = result[0]
            long_name = quote_data.get("quoteType", {}).get("longName")
            financial_data = quote_data.get("financialData")

            if not financial_data:
                print(f"Não foi possível encontrar dados financeiros para o ticker {ticker}")
                return None

            return {
                'Ticker': ticker,
                'Name': long_name,
                'Price': financial_data.get('currentPrice', {}).get('raw'),
            }
        else:
            print(f"Erro ao buscar informações para o ticker {ticker}: {response.status}")
            return None


async def get_stock_quotes(tickers):
    base_url = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{}?modules=summaryProfile%2CfinancialData%2CquoteType%2CdefaultKeyStatistics%2CassetProfile%2CsummaryDetail&ssl=true"
    stock_data = []

    async with aiohttp.ClientSession() as session:
        tasks = []
        for ticker in tickers:
            url = base_url.format(ticker)
            tasks.append(asyncio.ensure_future(fetch_stock_info(session, url, ticker)))

        results = await asyncio.gather(*tasks)

    for result in results:
        if result:
            stock_data.append(result)

    return pd.DataFrame(stock_data, columns=['Ticker', 'Nome', 'Preço'])


if __name__ == "__main__":
    tickers = get_all_tickers()
    save_tickers_to_csv(tickers)

    tickers_from_csv = read_tickers_from_csv()
    tickers_with_suffix = add_suffix_to_tickers(tickers_from_csv)
    stock_data = asyncio.run(get_stock_quotes(tickers_with_suffix))

    # Atualize o ID da planilha e o nome da planilha conforme necessário
    sheet_id = '1_pZOasF7mjs-JtibgEusc1Bh80i2IQOcsEW0mCBoEHo'
    sheet_name = 'Açoes'
    save_df_to_sheet(stock_data, sheet_name, sheet_id)
