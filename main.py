from comprar import processar_acoes
from cotacao_acao import config_ini_cotacao
from get_contabil_data_pg import config_ini
from get_dividendos_by_fundamentus_acoes import config_ini_dividendos
from modelo_final import modelagem
from rank_ev_roic import rank_ev_roic


def modelagens_e_rank():
    targets = ['receita_liquida', 'lucro_liquido', 'roe', 'roic', 'margem_liquida', 'liquidez_corrente', 'p_vp',
               'ev_ebit', 'div_liq_ebit', 'div_liq_patr_liq', 'e_y']

    for target in targets:
        modelagem(target)

    # Calculo do RANK
    rank_ev_roic()

if __name__ == "__main__":
    config_ini_cotacao()
    config_ini_dividendos()
    config_ini()
    modelagens_e_rank()
    # COMPRA SIM ou NAO
    processar_acoes()
