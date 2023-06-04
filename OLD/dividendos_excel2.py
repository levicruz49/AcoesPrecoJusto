import pandas as pd
import yfinance as yf
import asyncio
import pytz

yf.pdr_override()


async def get_dividends_yfinance(ticker, period):
    stock = yf.Ticker(ticker)
    if hasattr(stock, 'dividends'):
        history = stock.history(period='max')
        if 'Dividends' in history.columns:
            dividends = history['Dividends']
        else:
            dividends = pd.Series(dtype='float64')

        if isinstance(dividends.index, pd.DatetimeIndex):
            dividends.index = dividends.index.tz_convert('America/Sao_Paulo')

        now = pd.Timestamp.now(tz=pytz.timezone('America/Sao_Paulo'))

        if period == '1y':
            dividends = dividends[dividends.index > (now - pd.DateOffset(years=1)).to_pydatetime()]
        elif period == '7y':
            dividends = dividends[dividends.index > (now - pd.DateOffset(years=6)).to_pydatetime()]
        elif period == 'max':
            pass
        else:
            return None

        if len(dividends) > 0:
            return round(dividends.sum(), 2)
        else:
            return None
    else:
        return None


async def main(tickers):
    dividend_data = {}
    for ticker in tickers:
        try:
            dividend_data[ticker] = {
                '1y': await get_dividends_yfinance(ticker, '1y'),
                '7y': await get_dividends_yfinance(ticker, '7y'),
                'max': await get_dividends_yfinance(ticker, 'max')
            }
        except Exception as e:
            print(f"Erro ao buscar dados para {ticker}: {e}")
            continue

    return dividend_data


# def update_spreadsheet(dividend_data, filename, sheet_name):
#     df = pd.read_excel(filename, sheet_name=sheet_name)
#
#     for i, ticker in enumerate(dividend_data.keys(), start=2):
#         ticker_without_suffix = ticker.replace('.SA', '')  # Remover o sufixo '.SA'
#         if ticker_without_suffix in df['Ticker'].str.strip().values:  # Remover espaços dos tickers na planilha
#             index = df[df['Ticker'].str.strip() == ticker_without_suffix].index[
#                 0]  # Usar tickers sem espaços para encontrar correspondência
#             if dividend_data[ticker].get('1y'):
#                 df.loc[index, 'Dv 12 meses'] = dividend_data[ticker]['1y']
#             if dividend_data[ticker].get('7y'):
#                 df.loc[index, 'Dv 7 Anos'] = dividend_data[ticker]['7y']
#             if dividend_data[ticker].get('max'):
#                 df.loc[index, 'Maximo'] = dividend_data[ticker]['max']
#
#     df.to_excel(filename, sheet_name=sheet_name, index=False)

def update_spreadsheet(dividend_data, filename, sheet_name):
    with pd.ExcelWriter(filename, engine='openpyxl', mode='w') as writer:  # open the file in write mode
        df = pd.DataFrame()

        for i, ticker in enumerate(dividend_data.keys(), start=2):
            ticker_without_suffix = ticker.replace('.SA', '')  # Remover o sufixo '.SA'
            if 'Ticker' in df.columns and ticker_without_suffix in df['Ticker'].str.strip().values:  # Remover espaços dos tickers na planilha
                index = df[df['Ticker'].str.strip() == ticker_without_suffix].index[0]  # Usar tickers sem espaços para encontrar correspondência
                if dividend_data[ticker].get('1y'):
                    df.loc[index, 'Dv 12 meses'] = dividend_data[ticker]['1y']
                if dividend_data[ticker].get('7y'):
                    df.loc[index, 'Dv 7 Anos'] = dividend_data[ticker]['7y']
                if dividend_data[ticker].get('max'):
                    df.loc[index, 'Maximo'] = dividend_data[ticker]['max']

        if not df.empty:  # only write to the sheet if df is not empty
            df.to_excel(writer, sheet_name=sheet_name, index=False)  # write to the specific sheet
            writer.save()  # save the file





if __name__ == "__main__":
    filename = "C:\\Users\\mrcr\\Desktop\\preco_justo.xlsx"
    sheet_name = "Acoes"

    # Obter lista de tickers da coluna A, começando na linha 2
    df = pd.read_excel(filename, sheet_name=sheet_name, header=0)
    tickers = df['Ticker'].dropna().astype(str).tolist()
    tickers_with_suffix = [ticker.strip() + ".SA" for ticker in tickers]

    # Obter dados de dividendos
    dividend_data = asyncio.run(main(tickers_with_suffix))

    # Atualizar a planilha com os dados de dividendos
    update_spreadsheet(dividend_data, filename, sheet_name)
