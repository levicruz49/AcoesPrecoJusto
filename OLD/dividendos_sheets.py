import asyncio
import pandas as pd
import pytz
import time
from google.oauth2 import service_account
import gspread
import yfinance as yf


# Estabelece a conexão com a planilha do Google
def conn_sheet():
    KEY_FILE = '/acoessempre-2a81866e7af2.json'
    SHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    credentials = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SHEET_SCOPES)

    return gspread.authorize(credentials)


async def get_dividends_yfinance(ticker, period):
    stock = yf.Ticker(ticker)
    try:
        dividends = stock.history(period='max').Dividends
        dividends.index = dividends.index.tz_convert('America/Sao_Paulo')

        now = pd.Timestamp.now(tz=pytz.timezone('America/Sao_Paulo'))

        if period == '1y':
            dividends = dividends[dividends.index > now - pd.DateOffset(years=1)]
        elif period == '6y':
            dividends = dividends[dividends.index > now - pd.DateOffset(years=6)]
        elif period == 'max':
            pass
        else:
            return None

        if len(dividends) > 0:
            return round(dividends.sum(), 2)
        else:
            return None
    except:
        return None


# Função principal que busca os dividendos dos ativos
async def main(tickers_with_suffix):
    dividend_data = {'Ticker': [], '12 Months': [], '72 Months': [], 'Max': []}

    for ticker in tickers_with_suffix:
        dividend_data['Ticker'].append(ticker.rstrip(".SA"))
        dividend_data['12 Months'].append(await get_dividends_yfinance(ticker, '1y'))
        dividend_data['72 Months'].append(await get_dividends_yfinance(ticker, '6y'))
        dividend_data['Max'].append(await get_dividends_yfinance(ticker, 'max'))
        time.sleep(1)  # pausa de 1 segundo para evitar limites de taxa

    return dividend_data


# Adiciona um sufixo aos tickers
def add_suffix_to_tickers(tickers, suffix=".SA"):
    return [ticker + suffix for ticker in tickers]


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

    tickers_with_suffix = add_suffix_to_tickers(tickers)

    dividend_data = asyncio.run(main(tickers_with_suffix))

    # Criar DataFrame
    df_tickers = pd.DataFrame(dividend_data)

    # Exclui a coluna "Ticker" do DataFrame
    df_tickers = df_tickers.drop(columns=["Ticker"])

    # Atualizar os dados da planilha
    data = df_tickers.values.tolist()
    for i, row in enumerate(data, start=start_update_row):
        # Atualizar colunas C-E com os dados
        cells = sheet.range(f'C{i + 1}:E{i + 1}')
        for j, cell in enumerate(cells):
            cell_value = row[j]
            cell.value = '' if cell_value is None else str(cell_value).replace('.', ',')
        sheet.update_cells(cells)
