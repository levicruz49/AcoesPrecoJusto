from sqlalchemy import create_engine
from datetime import datetime


def conexao_pg():
    DATABASE_URI = 'postgresql+psycopg2://postgres:Embraer198@localhost/AcoesSempre'
    engine = create_engine(DATABASE_URI)
    return engine.raw_connection()


def get_tickers():
    conn = conexao_pg()
    cur = conn.cursor()
    cur.execute("SELECT ticker FROM public.Acoes")
    tickers = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return tickers


def get_tickers_cotacao():
    conn = conexao_pg()
    cur = conn.cursor()
    cur.execute("SELECT ticker FROM public.Acoes WHERE cotacao IS NULL")
    tickers = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return tickers


def get_tickers_inv_10():
    conn = conexao_pg()
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT acao FROM public.acoes_contabil ac1 WHERE ano >= '2009' AND acao NOT IN('BBSE3', 'CXSE3') AND \
        custos IS NULL AND NOT EXISTS (SELECT 1 FROM public.acoes_contabil ac2 WHERE ac2.acao = ac1.acao AND \
        ac2.ano >= '2009' AND \
        (ac2.custos IS NOT NULL OR \
        ac2.lucro_bruto IS NOT NULL OR \
        ac2.divida_liquida IS NOT NULL OR \
        ac2.margem_bruta IS NOT NULL OR \
        ac2.margem_ebitda IS NOT NULL OR \
        ac2.roic IS NOT NULL) )")
    tickers = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return tickers


def get_values_contabil(ticker, tipo):
    conn = conexao_pg()
    cur = conn.cursor()
    cur.execute(f"SELECT ano, {tipo}  FROM public.acoes_contabil WHERE acao = %s ORDER BY ano", (ticker,))
    rows = cur.fetchall()
    return rows


def insere_pg_inv10(dados, ticker):
    try:
        conn = conexao_pg()
        cur = conn.cursor()

        for ano, valores in dados.items():
            # substituir '' por None
            valores = [None if v == '' or v is None else float(
                v.replace('.', '').replace(',', '.')) if '.' in v or ',' in v else v for v in valores]
            receita_liquida, custos, lucro_bruto, lucro_liquido, ebitda, ebit, imposto, divida_bruta, divida_liquida, margem_bruta, margem_ebitda, margem_liquida, roe, roic = valores

            query = """
                        INSERT INTO public.acoes_contabil
                        (acao, ano, receita_liquida, custos, lucro_bruto, lucro_liquido, ebitda, ebit, imposto, divida_bruta, divida_liquida, margem_bruta, margem_ebitda, margem_liquida, roe, roic)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """

            cur.execute(query, (
                ticker, int(ano), receita_liquida, custos, lucro_bruto, lucro_liquido, ebitda, ebit, imposto,
                divida_bruta,
                divida_liquida, margem_bruta, margem_ebitda, margem_liquida, roe, roic))

        conn.commit()

    except Exception as e:
        print(f"Erro ao processar o ticker {ticker}: {e}")

    finally:
        if conn:
            cur.close()
            conn.close()


# def atualiza_pg_inv10(dados, ticker):
#     conn = conexao_pg()
#     cur = conn.cursor()
#
#     if dados[2]:
#         try:
#             dados = None if dados[2] == '' or dados[2] is None else float(
#                 dados[2].replace('.', '').replace(',', '.')) if '.' in dados[2] or ',' in dados[2] else dados[2]
#
#             query = """UPDATE public.acoes
#                         SET ev = %s
#                         WHERE ticker = %s """
#
#             cur.execute(query, (dados, ticker))
#
#             conn.commit()
#         except Exception as e:
#             print(f"Erro ao processar o update ticker {ticker}: {e} ")
#
#         finally:
#             if conn:
#                 cur.close()
#                 conn.close()
#     elif dados[0]:
#         try:
#             for ano, valores in dados[0].items():
#                 # Transformando lista de dicionários em um único dicionário
#                 valores_dict = {k: v for d in valores for k, v in d.items()}
#
#                 # Substituindo '' por None e transformando os valores em float
#                 for key, value in valores_dict.items():
#                     valores_dict[key] = None if value == '' or value is None else float(
#                         value.replace('.', '').replace(',', '.')) if '.' in value or ',' in value else value
#
#                 # Obtendo os valores desejados
#                 ev_ebit = valores_dict.get('EV/EBIT ')
#                 liquidez_corrente = valores_dict.get('LIQUIDEZ CORRENTE ')
#                 p_vp = valores_dict.get('P/VP ')
#                 lpa = valores_dict.get('LPA ')
#
#                 query = """
#                             UPDATE public.acoes_contabil
#                             SET ev_ebit = %s,
#                                 liquidez_corrente = %s,
#                                 p_vp = %s,
#                                 lpa = %s
#                             WHERE acao = %s AND ano = %s
#                             """
#
#                 cur.execute(query,
#                             (ev_ebit, liquidez_corrente, p_vp, lpa, ticker, int(ano)))
#
#         except Exception as e:
#             print(f"Erro ao processar o update no dados 0 ticker {ticker}: {e} ")
#
#         conn.commit()
#
#         try:
#             for ano, valores_2 in dados[1].items():
#                 # substituir '' por None
#                 valores_dict_2 = {k: v for d in valores_2 for k, v in d.items()}
#
#                 # Substituindo '' por None e transformando os valores em float
#                 for key, value in valores_dict_2.items():
#                     valores_dict_2[key] = None if value == '' or value is None else float(
#                         value.replace('.', '').replace(',', '.')) if '.' in value or ',' in value else value
#
#                 # Obtendo os valores desejados
#                 custos = valores_dict_2.get('Custos - (R$)')
#                 lucro_bruto = valores_dict_2.get('Lucro Bruto - (R$)')
#                 divida_liquida = valores_dict_2.get('Dívida Líquida - (R$)')
#                 margem_bruta = valores_dict_2.get('Margem Bruta - (%)')
#                 margem_ebitda = valores_dict_2.get('Margem Ebitda - (%)')
#                 roic = valores_dict_2.get('ROIC - (%)')
#
#                 query = """
#                             UPDATE public.acoes_contabil
#                             SET custos = %s,
#                                 lucro_bruto = %s,
#                                 divida_liquida = %s,
#                                 margem_bruta = %s,
#                                 margem_ebitda = %s,
#                                 roic = %s
#                             WHERE acao = %s AND ano = %s
#                             """
#
#                 cur.execute(query,
#                             (custos, lucro_bruto, divida_liquida, margem_bruta, margem_ebitda, roic, ticker, int(ano)))
#             conn.commit()
#         except Exception as e:
#             print(f"Erro ao processar o update no dados 1 ticker {ticker}: {e}")
#
#
#         finally:
#             if conn:
#                 cur.close()
#                 conn.close()
def atualiza_pg_inv10(dados, ticker):
    conn = conexao_pg()
    cur = conn.cursor()

    dados_0, dados_1, dados_2 = dados  # Desempacotando a lista de dados

    count_roic_0 = 0
    count_roic_1 = 0

    roics_0 = []
    roics_1 = []

    try:
        if dados_2:
            dados_2 = None if dados_2 == '' or dados_2 is None else float(
                dados_2.replace('.', '').replace(',', '.')) if '.' in dados_2 or ',' in dados_2 else dados_2

            query = """UPDATE public.acoes
                        SET ev = %s
                        WHERE ticker = %s """

            cur.execute(query, (dados_2, ticker))

        if dados_0:
            for ano, valores in dados_0.items():
                # Transformando lista de dicionários em um único dicionário
                valores_dict = {k: v for d in valores for k, v in d.items()}

                # Substituindo '' por None e transformando os valores em float
                for key, value in valores_dict.items():
                    valores_dict[key] = None if value == '' or value is None else float(
                        value.replace('.', '').replace(',', '.')) if '.' in value or ',' in value else value

                roic_0 = valores_dict.get('ROIC ')
                if roic_0 is not None and roic_0 > 0:
                    roics_0.append((ano, roic_0))
                    count_roic_0 += 1

                # Obtendo os valores desejados
                ev_ebit = valores_dict.get('EV/EBIT ')
                liquidez_corrente = valores_dict.get('LIQUIDEZ CORRENTE ')
                p_vp = valores_dict.get('P/VP ')
                lpa = valores_dict.get('LPA ')
                roic_0 = valores_dict.get('ROIC ')

                if roic_0 is not None and roic_0 > 0:
                    count_roic_0 += 1

                query = """
                            UPDATE public.acoes_contabil
                            SET ev_ebit = %s,
                                liquidez_corrente = %s,
                                p_vp = %s,
                                lpa = %s
                            WHERE acao = %s AND ano = %s
                            """

                cur.execute(query,
                            (ev_ebit, liquidez_corrente, p_vp, lpa, ticker, int(ano)))

        if dados_1:
            for ano, valores_2 in dados_1.items():
                # substituir '' por None
                valores_dict_2 = {k: v for d in valores_2 for k, v in d.items()}

                # Substituindo '' por None e transformando os valores em float
                try:
                    for key, value in valores_dict_2.items():
                        if isinstance(value, str):  # Adicionando esta verificação
                            value = value.replace('.', '').replace(',', '.')
                            valores_dict_2[key] = None if value == '' else float(value) if '.' in value else value
                        else:
                            valores_dict_2[key] = value
                except Exception as e:
                    print(f'Erro no try-except de Substituindo por None e transformando os valores em float, erro{e}')

                roic_1 = valores_dict_2.get('ROIC - (%)')
                if roic_1 is not None and roic_1 > 0:
                    roics_1.append((ano, roic_1))
                    count_roic_1 += 1

                # Obtendo os valores desejados
                custos = valores_dict_2.get('Custos - (R$)')
                lucro_bruto = valores_dict_2.get('Lucro Bruto - (R$)')
                divida_liquida = valores_dict_2.get('Dívida Líquida - (R$)')
                margem_bruta = valores_dict_2.get('Margem Bruta - (%)')
                margem_ebitda = valores_dict_2.get('Margem Ebitda - (%)')
                roic_1 = valores_dict_2.get('ROIC - (%)')

                if roic_1 is not None and roic_1 > 0:
                    count_roic_1 += 1

                query = """
                            UPDATE public.acoes_contabil
                            SET custos = %s,
                                lucro_bruto = %s,
                                divida_liquida = %s,
                                margem_bruta = %s,
                                margem_ebitda = %s
                            WHERE acao = %s AND ano = %s
                            """

                cur.execute(query,
                            (custos, lucro_bruto, divida_liquida, margem_bruta, margem_ebitda, ticker, int(ano)))

        # No final do código:
        roics = roics_0 if count_roic_0 >= count_roic_1 else roics_1

        for ano, roic in roics:
            query = """
                        UPDATE public.acoes_contabil
                        SET roic = %s
                        WHERE acao = %s AND ano = %s
                        """
            cur.execute(query, (roic, ticker, int(ano)))

        conn.commit()
    except Exception as e:
        print(f"Erro ao processar o update ticker {ticker}: {e} ")
    finally:
        if conn:
            cur.close()
            conn.close()


def atualiza_ev_inv10(dados, ticker):
    conn = conexao_pg()
    cur = conn.cursor()
    try:
        dados = None if dados == '' or dados is None else float(
            dados.replace('.', '').replace(',', '.')) if '.' in dados or ',' in dados else dados

        query = """UPDATE public.acoes
                    SET ev = %s
                    WHERE ticker = %s """

        cur.execute(query, (dados, ticker))

        conn.commit()
    except Exception as e:
        print(f"Erro ao processar o update ticker {ticker}: {e} ")

    finally:
        if conn:
            cur.close()
            conn.close()


def insere_pg(dados, ticker):
    try:
        conn = conexao_pg()
        cur = conn.cursor()

        for ano, valores in dados.items():
            patrimonio_liquido = -1 if valores.get('Patrimônio Líquido', 'P') == 'P' else float(
                str(valores.get('Patrimônio Líquido', '0')).replace(',', '.'))
            receita_inter_fin = -1 if valores.get('Receita Inter. Fin.', 'P') == 'P' else float(
                str(valores.get('Receita Inter. Fin.', '0')).replace(',', '.'))
            margem_liquida = -1 if valores.get('Margem Líquida', 'P') == 'P' else float(
                str(valores.get('Margem Líquida', '0')).replace(',', '.'))
            roe = -1 if valores.get('ROE', 'P') == 'P' else float(str(valores.get('ROE', '0')).replace(',', '.'))
            payout = -1 if valores.get('Payout', 'P') == 'P' else float(
                str(valores.get('Payout', '0')).replace(',', '.'))
            ebitda = -1 if valores.get('EBITDA', 'P') == 'P' else float(
                str(valores.get('EBITDA', '0')).replace(',', '.'))
            ebit = -1 if valores.get('EBIT', 'P') == 'P' else float(str(valores.get('EBIT', '0')).replace(',', '.'))
            impostos = -1 if valores.get('Impostos', 'P') == 'P' else float(
                str(valores.get('Impostos', '0')).replace(',', '.'))
            divida = -1 if valores.get('Dívida', 'P') == 'P' else float(
                str(valores.get('Dívida', '0')).replace(',', '.'))
            lucro_liquido = -1 if valores.get('Lucro Líquido', 'P') == 'P' else float(
                str(valores.get('Lucro Líquido', '0')).replace(',', '.'))

            query = """
                        INSERT INTO public.acoes_contabil
                        (acao, ano, patrimonio_liquido, receita_liquida, lucro_liquido, margem_liquida, roe, payout, ebitda, ebit, imposto, divida_bruta)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """

            cur.execute(query, (
                ticker, int(ano), patrimonio_liquido, receita_inter_fin, lucro_liquido, margem_liquida, roe, payout,
                ebitda, ebit, impostos,
                divida))

        conn.commit()

    except Exception as e:
        print(f"Erro ao salvar no banco o ticker {ticker}: {e}")

    finally:
        if conn:
            cur.close()
            conn.close()


def insere_classificacao_pg(crescente_str, ticker, tipo, motivo):
    data = datetime.now()  # Adicione essa linha
    conn = conexao_pg()
    cur = conn.cursor()
    # Aqui poderia inserir a variável `crescente` no seu banco de dados.
    cur.execute(f"UPDATE public.acoes SET {tipo} = %s WHERE ticker = %s", (crescente_str, ticker))
    if motivo:
        cur.execute(f"INSERT INTO public.motivos_para_nao(acao, data, modelo_motivo) VALUES (%s, %s, %s)",
                    (ticker, data, motivo))

    conn.commit()


def atualiza_dividendos(proventos_1y, proventos_6y, proventos_max, ticker):
    conn = conexao_pg()
    cur = conn.cursor()
    try:
        update_query = """
                                            UPDATE Acoes 
                                            SET div_12_meses = %s, med_div_6_anos = %s, maximo_div = %s
                                            WHERE ticker = %s
                                            """
        cur.execute(update_query, (proventos_1y, proventos_6y, proventos_max, ticker))
        conn.commit()
    except Exception as e:
        print(f"Erro ao inserir o dividendo do ticker {ticker}: {e} ")

    finally:
        if conn:
            cur.close()
            conn.close()


def insere_previsao_e_motivo_tb_motivos_aportes(ticker, prediction, target):
    conn = conexao_pg()
    cur = conn.cursor()

    upsert_query = f"""
                        INSERT INTO public.motivos_aportes (acao, data, modelo_motivo, target) 
                        VALUES ('{ticker}', NOW(), '{prediction}', '{target}') 
                        ON CONFLICT (acao, data, target) DO UPDATE SET modelo_motivo = '{prediction}';
                        """
    cur.execute(upsert_query)
    conn.commit()


def atualiza_classificacao_acoes(ticker, result, target):
    conn = conexao_pg()
    cur = conn.cursor()

    insert_query = f"UPDATE public.acoes SET {target} = '{result['modelo']}' WHERE ticker = '{ticker}'"
    cur.execute(insert_query)
    conn.commit()
