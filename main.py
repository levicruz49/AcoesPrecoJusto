from cotacao_acao import config_ini_cotacao
from get_contabil_data_pg import config_ini
from modelo_final import modelagem
from rank_ev_roic import rank_ev_roic


def modelagens_e_rank():

    # modelagem('receita_liquida')
    # modelagem('lucro_liquido')
    # modelagem('roe')
    # modelagem('roic')
    # modelagem('margem_liquida')
    # modelagem('liquidez_corrente')
    # modelagem('p_vp')
    # modelagem('ev_ebit')
    # modelagem('div_liq_ebit')
    # modelagem('div_liq_patr_liq')
    # modelagem('e_y')

    # Calculo do RANK
    rank_ev_roic()

if __name__ == "__main__":
    config_ini_cotacao()
    config_ini()
    modelagens_e_rank()

