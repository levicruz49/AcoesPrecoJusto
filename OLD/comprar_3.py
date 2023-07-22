import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from keras.models import Sequential
from keras.layers import Dense
from keras.callbacks import EarlyStopping

from facade import conexao_pg

# Conexão com o PostgreSQL
conn = conexao_pg()

# Leitura dos dados da tabela "acoes_contabil"
query_acoes_contabil = """
SELECT id, acao, ano, receita_liquida, custos, lucro_bruto, lucro_liquido, ebitda, ebit, imposto,
       divida_bruta, divida_liquida, margem_bruta, margem_ebitda, margem_liquida, roe, roic,
       patrimonio_liquido, payout, ev_ebit, liquidez_corrente, p_vp, lpa
FROM public.acoes_contabil
"""

df = pd.read_sql(query_acoes_contabil, conn)
df = df.fillna(0)

# Selecionar as colunas relevantes para o modelo
features = ['receita_liquida', 'ebit', 'imposto', 'divida_liquida', 'margem_ebitda', 'margem_liquida', 'roic',
            'payout', 'ev_ebit', 'liquidez_corrente', 'p_vp', 'lpa']

X = df[features]

# Vamos assumir que é um problema de classificação binária para fins de exemplo
y = np.random.choice([0, 1], size=(len(df),))

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

model = Sequential()
model.add(Dense(64, activation='relu', input_shape=(X.shape[1],)))
model.add(Dense(64, activation='relu'))
model.add(Dense(1, activation='sigmoid'))

model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])

early_stopping = EarlyStopping(patience=5, restore_best_weights=True)

model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=100, batch_size=32, callbacks=[early_stopping])

_, accuracy = model.evaluate(X_test, y_test)
print(f"Acurácia do modelo: {accuracy}")

# As previsões agora são feitas no conjunto de dados completo
y_pred = model.predict(X)
df['previsao'] = y_pred.flatten()

# Agrupa por ação e calcula a média das previsões
df_agrupado = df.groupby('acao')['previsao'].mean().reset_index()

# Transforma as médias em "SIM" ou "NAO"
df_agrupado['comprar'] = df_agrupado['previsao'].apply(lambda x: 'SIM' if x > 0.5 else 'NAO')

# Exclui a coluna de previsões médias
df_agrupado = df_agrupado.drop('previsao', axis=1)

# Exportar o DataFrame para um arquivo JSON
df_agrupado.to_json('acoes_contabil_resultado.json', orient='records')

conn.close()
