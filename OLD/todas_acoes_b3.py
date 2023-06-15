import yfinance as yf
import investpy as inv
import gspread
from google.oauth2 import service_account
import pandas as pd
import asyncio
import aiohttp
import functools


def get_listed_companies():
    br = inv.stocks.get_stocks(country='Brazil')
    return br['symbol'].tolist()


def conn_sheet():
    KEY_FILE = '/acoessempre-2a81866e7af2.json'
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
    data = df.applymap(
        lambda x: str(x) if isinstance(x, float) else x).values.tolist()  # Converter o DataFrame em uma lista de listas
    cell_range = f'A2:{gspread.utils.rowcol_to_a1(len(data) + 1, len(header))}'
    cells = sheet.range(cell_range)
    for i, row in enumerate(data):
        for j, cell in enumerate(row):
            cells[i * len(header) + j].value = cell
    sheet.update_cells(cells)  # Atualizar todas as células de uma só vez


def get_tickers_from_sheet(sheet_name, sheet_id):
    gc = conn_sheet()
    sheet = gc.open_by_key(sheet_id).worksheet(sheet_name)

    tickers = sheet.col_values(1)
    return tickers[1:]  # Ignorar o cabeçalho (primeira linha)


async def get_stock_price_investpy(ticker):
    try:
        func = functools.partial(inv.get_stock_recent_data, stock=ticker, country='Brazil', as_json=False,
                                 order='ascending')
        stock_info = await loop.run_in_executor(None, func)
        return stock_info.iloc[-1]['Close']
    except Exception as e:
        print(f"Erro ao obter o preço da ação {ticker} com investpy: {e}")
        return None


async def get_stock_price_yfinance(ticker):
    try:
        stock_info = yf.Ticker(f'{ticker}.SA')
        stock_hist = stock_info.history(period='1d')
        return stock_hist.iloc[-1]['Close']
    except Exception as e:
        print(f"Erro ao obter o preço da ação {ticker} com yfinance: {e}")
        return None


async def get_stock_price(ticker):
    price = await get_stock_price_investpy(ticker)
    if price is None:
        price = await get_stock_price_yfinance(ticker)
    return price


async def get_stock_prices(tickers):
    prices = []
    async with aiohttp.ClientSession() as session:
        for ticker in tickers:
            price = await get_stock_price(ticker)
            prices.append(price)
    return prices


def read_tickers_from_sheet(sheet_id, sheet_name):
    gc = conn_sheet()
    sheet = gc.open_by_key(sheet_id).worksheet(sheet_name)

    tickers = []
    for row in sheet.get_all_values()[1:]:
        tickers.append(row[0])
    return tickers


if __name__ == "__main__":
    # Atualize o ID da planilha e o nome da planilha conforme necessário
    sheet_id = '1_pZOasF7mjs-JtibgEusc1Bh80i2IQOcsEW0mCBoEHo'
    sheet_name = 'Açoes'

    tickers = get_listed_companies()
    df_tickers = pd.DataFrame(tickers, columns=['Ticker'])

    loop = asyncio.get_event_loop()
    prices = loop.run_until_complete(get_stock_prices(tickers))

    # Arredonda os preços para duas casas decimais
    rounded_prices = [round(price, 2) if price is not None else None for price in prices]

    # Adiciona a nova coluna "Preco Yfi-investpy" com os preços obtidos do yfinance ou investpy
    df_tickers['Preco Yfi-investpy'] = rounded_prices

    save_df_to_sheet(df_tickers, sheet_name, sheet_id)

