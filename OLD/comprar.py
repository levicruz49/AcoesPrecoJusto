import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.compose import make_column_transformer

from facade import conexao_pg

conn = conexao_pg()

# Codificação one-hot das variáveis categóricas
categorical_columns = ["receita_liquida", "lucro_liquido", "roic", "margem_liquida",
                       "div_liq_ebit", "ev_ebit", "div_liq_patr_liq", "roe",
                       "liquidez_corrente", "p_vp", "e_y"]
encoder = make_column_transformer(
    (OneHotEncoder(), categorical_columns),
    remainder="passthrough",
)

# Leitura e processamento dos dados
df = pd.read_sql('SELECT id, COTACAO, DIV_12_MESES, PRECO_JUSTO_BAZIN, PRECO_JUSTO_6_ANOS, \
                  RECEITA_LIQUIDA, LUCRO_LIQUIDO, ROIC, MARGEM_LIQUIDA, DIV_LIQ_EBIT, \
                  EV_EBIT, DIV_LIQ_PATR_LIQ, ROE, LIQUIDEZ_CORRENTE, P_VP, E_Y, rank, ev, COMPRAR \
                  FROM PUBLIC.ACOES', conn)

# Substituir todos os NaNs por 0
df = df.fillna(0)

# Substituir todos os NaNs pela média da coluna
df["rank"] = df["rank"].fillna(df["rank"].mean())

# Descartar qualquer linha que contenha um NaN
df = df.dropna()

df_encoded = encoder.fit_transform(df.drop(columns=["comprar", "id", "ev"]))

# Separação em conjuntos de treinamento e teste
X_train, X_test, y_train, y_test = train_test_split(
    df_encoded,
    df["comprar"],
    test_size=0.3,
    random_state=42,
)

# Treinamento do modelo
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Avaliação do modelo
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"Acurácia do modelo: {accuracy}")
