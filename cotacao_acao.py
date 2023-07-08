import yfinance as yf
import json
import datetime

from facade import get_tickers, conexao_pg


def update_cotacao(ticker):
    ticker = ticker + ".SA"
    tickerData = yf.Ticker(ticker)
    cotacao = round(tickerData.history(period='1d').Close[0], 2)

    conn = conexao_pg()
    cur = conn.cursor()

    update_query = """
    UPDATE Acoes 
    SET cotacao = %s
    WHERE ticker = %s
    """
    cur.execute(update_query, (cotacao, ticker[:-3]))  # removemos ".SA" para fazer a atualização no Postgres

    conn.commit()
    cur.close()
    conn.close()


def config_ini_cotacao():
    all_tickers = get_tickers()

    try:
        with open('last_update_cotacao.json', 'r') as f:
            last_update = datetime.datetime.strptime(json.load(f), '%Y-%m-%d')
    except FileNotFoundError:
        last_update = datetime.datetime(2000, 1, 1)

    today = datetime.datetime.now().date()
    if today != last_update.date():
        for ticker in all_tickers:
            update_cotacao(ticker)

        # Atualizando a data da última atualização
        with open('last_update_cotacao.json', 'w') as f:
            json.dump(str(today), f)


if __name__ == "__main__":
    config_ini_cotacao()