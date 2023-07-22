import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
import json

# Carregando os dados do arquivo json
with open('../JSONS/precos.json', 'r') as f:
    data = json.load(f)

# Transformando os dados em um DataFrame
df = pd.DataFrame(data['DATA']) # Carregando corretamente os dados

# Convertendo as datas para o formato correto
df['date'] = pd.to_datetime(df['date'])

# Criando novas colunas com o ano, mês e dia
df['Ano'] = df['date'].dt.year
df['Mes'] = df['date'].dt.month
df['Dia'] = df['date'].dt.day

# Removendo a coluna de datas
df = df.drop('date', axis=1) # Usando o nome correto da coluna

# Separando os dados em conjuntos de treino e teste
X = df.drop('value', axis=1) # Usando o nome correto da coluna
y = df['value'] # Usando o nome correto da coluna
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Criando e treinando o modelo RandomForestRegressor
rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)

# Criando e treinando o modelo GradientBoostingRegressor
gb_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
gb_model.fit(X_train, y_train)

# Fazendo as previsões
rf_predictions = rf_model.predict(X_test)
gb_predictions = gb_model.predict(X_test)

# Calculando o erro médio absoluto de cada modelo
rf_mae = mean_absolute_error(y_test, rf_predictions)
gb_mae = mean_absolute_error(y_test, gb_predictions)

print(f'Erro médio absoluto do modelo RandomForestRegressor: {rf_mae}')
print(f'Erro médio absoluto do modelo GradientBoostingRegressor: {gb_mae}')

# Criando um DataFrame com as características da data "30/06/2023"
data_pred = pd.DataFrame({
    'Ano': [2023],
    'Mes': [6],
    'Dia': [30]
})

# Fazendo a previsão com o modelo RandomForestRegressor
rf_pred = rf_model.predict(data_pred)
print(f'Previsão do modelo RandomForestRegressor para 30/06/2023: {rf_pred[0]}')

# Fazendo a previsão com o modelo GradientBoostingRegressor
gb_pred = gb_model.predict(data_pred)
print(f'Previsão do modelo GradientBoostingRegressor para 30/06/2023: {gb_pred[0]}')
