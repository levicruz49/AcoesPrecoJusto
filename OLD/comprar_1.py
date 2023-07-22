import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from keras.models import Sequential
from keras.layers import Dense
from keras.callbacks import EarlyStopping
from facade import conexao_pg

# Conexão com o PostgreSQL
conn = conexao_pg()

# Leitura dos dados da tabela "acoes"
query_acoes = """
SELECT id, TICKER, COTACAO, DIV_12_MESES, PRECO_JUSTO_BAZIN, PRECO_JUSTO_6_ANOS,
       RECEITA_LIQUIDA, LUCRO_LIQUIDO, ROIC, MARGEM_LIQUIDA, DIV_LIQ_EBIT,
       EV_EBIT, DIV_LIQ_PATR_LIQ, ROE, LIQUIDEZ_CORRENTE, P_VP, E_Y, rank, ev, COMPRAR
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

# Fechar a conexão com o banco de dados
conn.close()

# Combinar os dados das tabelas "acoes" e "acoes_contabil"
columns_to_keep = ['ticker', 'cotacao', 'div_12_meses', 'preco_justo_bazin', 'preco_justo_6_anos', 'receita_liquida',
                   'lucro_liquido', 'roic', 'margem_liquida', 'div_liq_ebit', 'ev_ebit', 'div_liq_patr_liq',
                   'roe', 'liquidez_corrente', 'p_vp']
df = df_acoes.merge(df_acoes_contabil, left_on='ticker', right_on='acao', suffixes=('_acoes', '_acoes_contabil'))



# Selecionar as colunas relevantes para o modelo
features = ['receita_liquida_acoes', 'lucro_liquido_acoes', 'roic_acoes', 'margem_liquida_acoes', 'div_liq_ebit',
            'ev_ebit_acoes', 'div_liq_patr_liq', 'roe_acoes', 'liquidez_corrente_acoes', 'p_vp_acoes',
            'rank', 'preco_justo_6_anos']


# Preparar os dados de entrada e saída
X = df[features].values
y = df['comprar'].values

# Codificar as classes da coluna "comprar"
le = LabelEncoder()
y = le.fit_transform(y)

# Dividir os dados em conjunto de treinamento e teste
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Padronizar os dados de entrada
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# Criar o modelo de redes neurais
model = Sequential()
model.add(Dense(64, activation='relu', input_shape=(len(features),)))
model.add(Dense(64, activation='relu'))
model.add(Dense(3, activation='softmax'))

# Compilar o modelo
model.compile(loss='sparse_categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

# Definir o Early Stopping para interromper o treinamento se não houver melhora na precisão
early_stopping = EarlyStopping(patience=5, restore_best_weights=True)

# Treinar o modelo
model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=100, batch_size=32, callbacks=[early_stopping])

# Avaliar o modelo no conjunto de teste
_, accuracy = model.evaluate(X_test, y_test)
print(f"Acurácia do modelo: {accuracy}")

# Fazer previsões no conjunto de teste
y_pred = model.predict(X_test)
y_pred_labels = np.argmax(y_pred, axis=1)
predicted_classes = le.inverse_transform(y_pred_labels)

# Atualizar a coluna "comprar" na tabela "acoes"
df_acoes['comprar'] = predicted_classes

# Atualizar a tabela "acoes" no banco de dados
conn = conexao_pg()
for index, row in df_acoes.iterrows():
    update_query = f"""
    UPDATE public.acoes
    SET comprar = '{row['comprar']}'
    WHERE id = {row['id']}
    """
    conn.execute(update_query)
conn.close()
