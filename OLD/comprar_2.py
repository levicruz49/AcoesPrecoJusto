import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from keras.models import Sequential
from keras.layers import Dense
from keras.callbacks import EarlyStopping
from sqlalchemy import create_engine, text

from facade import conexao_pg

# Conexão com o PostgreSQL
conn = conexao_pg()

# Leitura dos dados da tabela "acoes"
query_acoes = """
SELECT id, ticker, COTACAO, DIV_12_MESES, PRECO_JUSTO_BAZIN, PRECO_JUSTO_6_ANOS,
       RECEITA_LIQUIDA, LUCRO_LIQUIDO, ROIC, MARGEM_LIQUIDA, DIV_LIQ_EBIT,
       EV_EBIT, DIV_LIQ_PATR_LIQ, ROE, LIQUIDEZ_CORRENTE, P_VP, E_Y, rank, ev, comprar
FROM public.acoes
"""

df_acoes = pd.read_sql(query_acoes, conn)

# Leitura dos dados da tabela "acoes_contabil"
query_acoes_contabil = """
SELECT id, acao, ano, receita_liquida, custos, lucro_bruto, lucro_liquido, ebitda, ebit, imposto,
       divida_bruta, divida_liquida, margem_bruta, margem_ebitda, margem_liquida, roe, roic,
       patrimonio_liquido, payout, ev_ebit, liquidez_corrente, p_vp, lpa
FROM public.acoes_contabil
"""

df_acoes_contabil = pd.read_sql(query_acoes_contabil, conn)
df_acoes_contabil = df_acoes_contabil.fillna(0)

# Combinar os dados das tabelas "acoes" e "acoes_contabil"
df = df_acoes.merge(df_acoes_contabil, left_on='ticker', right_on='acao', suffixes=('_acoes', '_acoes_contabil'))

df = df.dropna(subset=['rank'])

df['rank'].fillna(0, inplace=True)
df['comprar'].fillna(0, inplace=True)

# Selecionar as colunas relevantes para o modelo
features = ['receita_liquida_acoes', 'lucro_liquido_acoes', 'roic_acoes', 'margem_liquida_acoes', 'div_liq_ebit',
            'ev_ebit_acoes', 'div_liq_patr_liq', 'roe_acoes', 'liquidez_corrente_acoes', 'p_vp_acoes',
            'rank', 'preco_justo_6_anos']

# Para cada recurso categórico em suas características...
for column in features:
    if df[column].dtype == 'object':  # Se a coluna for do tipo 'object' (que é equivalente a str)
        # Execute a codificação one-hot e junte-a ao DataFrame existente
        df = pd.concat([df, pd.get_dummies(df[column], prefix=column)], axis=1)
        # Em seguida, solte a coluna categórica original
        df = df.drop(column, axis=1)

# Crie uma nova lista de características
new_features = [col for col in df.columns if any(feature in col for feature in features)]

# Use essa nova lista para selecionar as colunas de df para X
X = df[new_features]

# Preparar os dados de saída
y = df['comprar']

# Dividir os dados em conjunto de treinamento e teste
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Padronizar os dados de entrada
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# Verificar os tamanhos dos dados antes do treinamento do modelo
print("Tamanho dos dados de treinamento:")
print("X_train:", X_train.shape)
print("y_train:", y_train.shape)

# Criar o modelo de redes neurais
model = Sequential()
model.add(Dense(64, activation='relu', input_shape=(X.shape[1],)))
model.add(Dense(64, activation='relu'))
model.add(Dense(1, activation='sigmoid'))  # Mudar para sigmoid para problema de classificação binária

# Compilar o modelo
model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])  # Mudar para binary_crossentropy

# Definir o Early Stopping para interromper o treinamento se não houver melhora na precisão
early_stopping = EarlyStopping(patience=5, restore_best_weights=True)

# Treinar o modelo
model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=100, batch_size=32, callbacks=[early_stopping])

# Avaliar o modelo no conjunto de teste
_, accuracy = model.evaluate(X_test, y_test)
print(f"Acurácia do modelo: {accuracy}")

# Fazer previsões no conjunto de teste
y_pred = model.predict(X_test)
y_pred_labels = ["SIM" if pred > 0.5 else "NAO" for pred in y_pred]  # Atribuir rótulos com base na saída do modelo

# Verificar os tamanhos dos dados após a previsão
print("Tamanho dos dados após a previsão:")
print("y_pred_labels:", len(y_pred_labels))
print("df_acoes:", df_acoes.shape)

# Atualizar a coluna "comprar" na tabela "acoes"
df_acoes['comprar'] = y_pred_labels

# Verificar o tamanho dos dados após a atualização
print("Tamanho dos dados após a atualização:")
print("df_acoes:", df_acoes.shape)

# Atualizar a tabela "acoes" no banco de dados
for index, row in df_acoes.iterrows():
    update_query = f"""
    UPDATE public.acoes
    SET comprar = '{row['comprar']}'
    WHERE id = {row['id']}
    """
    conn.execute(update_query)
conn.close()
