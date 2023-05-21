import fundamentus


def get_net_income(ticker):
    rs = fundamentus.get_detalhes_papel(ticker)
    return rs

if __name__ == "__main__":
    ticker = 'PETR4'
    net_income = get_net_income(ticker)
    print(f"Net income for {ticker}: {net_income.LPA[0]}")
