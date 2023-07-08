from cotacao_acao import config_ini_cotacao
from get_contabil_data_pg import config_ini
from modelo_final import modelagem

def modelagens():

    # modelagem('receita_liquida')
    # modelagem('lucro_liquido')
    modelagem('roe')

if __name__ == "__main__":
    config_ini_cotacao()
    config_ini()
    modelagens()
