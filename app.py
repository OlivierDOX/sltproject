import streamlit as st
import pandas as pd
from itertools import combinations_with_replacement
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, PULP_CBC_CMD

st.title("Cálculo de Planos de Corte de Bobinas")

# Entradas do usuário
limite_inferior = st.text_input("Limite Inferior (%)", "90")
limite_superior = st.text_input("Limite Superior (%)", "130")

try:
    limite_inferior = float(limite_inferior) / 100
    limite_superior = float(limite_superior) / 100
except ValueError:
    st.error("Os limites inferior e superior devem ser números válidos em porcentagem.")
    st.stop()

# Largura da bobina fixa
larguras_bobina = [1192, 1191, 1190, 1189, 1188]
peso_bobina = 17715

# Entrada de demandas
demands_input = st.text_area("Demandas (formato: largura ; peso por linha, ex: 105 ; 10000)", "105 ; 10000\n197 ; 30000")
# Processar demandas
demands = []
for line in demands_input.strip().split("\n"):
    try:
        width, weight = map(int, line.split(";"))
        demands.append({"width": width, "weight": weight})
    except ValueError:
        st.error("Formato de demandas inválido! Use largura ; peso por linha.")
        st.stop()

# Definições dos produtos
produtos = {
    105: "Perfil UDC Enrijecido 50x25x10x2,00x6000mm",
    170: "Perfil UDC Enrijecido 75x40x15x2,00x6000mm",
    197: "Perfil UDC Enrijecido 100x40x15x2,00x6000mm",
    219: "Perfil UDC Enrijecido 100x50x17x2,00x6000mm",
    244: "Perfil UDC Enrijecido 127x50x17x2,00x6000mm",
    264: "Perfil UDC Enrijecido 150x50x17x2,00x6000mm",
    295: "Perfil UDC Enrijecido 150x60x20x2,00x6000mm",
    375: "Perfil UDC Enrijecido 200x75x25x2,00x6000mm",
    93: "Perfil UDC Simples 50x25x2,00x6000mm",
    122: "Perfil UDC Simples 68x30x2,00x6000mm",
    148: "Perfil UDC Simples 92x30x2,00x6000mm",
    173: "Perfil UDC Simples 100x40x2,00x6000mm",
    192: "Perfil UDC Simples 100x50x2,00x6000mm",
    217: "Perfil UDC Simples 127x50x2,00x6000mm",
    242: "Perfil UDC Simples 150x50x2,00x6000mm",
    343: "Perfil UDC Simples 200x75x2,00x6000mm"
}

larguras_slitters = list(produtos.keys())

def encontra_combinacoes_possiveis(larguras_slitters, largura_bobina):
    combinacoes = []
    for n in range(1, largura_bobina // min(larguras_slitters) + 1):
        for combinacao in combinations_with_replacement(larguras_slitters, n):
            if sum(combinacao) == largura_bobina:
                combinacoes.append(combinacao)
    return combinacoes

def resolver_problema_corte(larguras_slitters, largura_bobina, peso_bobina, demandas):
    proporcao = peso_bobina / largura_bobina
    combinacoes = encontra_combinacoes_possiveis(larguras_slitters, largura_bobina)
    if not combinacoes:
        return None
    problema = LpProblem("Problema_de_Corte", LpMinimize)
    x = LpVariable.dicts("Plano", range(len(combinacoes)), lowBound=0, cat="Integer")
    problema += lpSum(x[i] for i in range(len(combinacoes))), "Minimizar_Bobinas"
    for demanda in demandas:
        largura = demanda["width"]
        peso_necessario = demanda["weight"]
        problema += (
            lpSum(
                x[i] * combinacao.count(largura) * proporcao * largura
                for i, combinacao in enumerate(combinacoes)
            ) >= peso_necessario * limite_inferior,
            f"Atender_Minima_{largura}",
        )
        problema += (
            lpSum(
                x[i] * combinacao.count(largura) * proporcao * largura
                for i, combinacao in enumerate(combinacoes)
            ) <= peso_necessario * limite_superior,
            f"Atender_Maxima_{largura}",
        )
    problema.solve(PULP_CBC_CMD(msg=False))
    if problema.status != 1:
        return None
    resultado = []
    for i, combinacao in enumerate(combinacoes):
        if x[i].varValue > 0:
            resultado.append({
                "Plano de Corte": combinacao,
                "Quantidade": int(x[i].varValue),
                "Largura Total": sum(combinacao)
            })
    return pd.DataFrame(resultado)

# Botão para calcular
if st.button("Calcular"):
    melhor_resultado = None
    melhor_largura = None
    for largura_bobina in larguras_bobina:
        resultado = resolver_problema_corte(larguras_slitters, largura_bobina, peso_bobina, demands)
        if resultado is not None:
            melhor_resultado = resultado
            melhor_largura = largura_bobina
            break
    if melhor_resultado is not None:
        st.subheader("Melhor largura de bobina")
        st.write(f"{melhor_largura} mm")
        st.subheader("Resultado dos Planos de Corte")
        st.dataframe(melhor_resultado)
        # Gerar arquivo TXT
        resultado_txt = melhor_resultado.to_string(index=False)
        st.download_button(
            label="Baixar Plano de Corte (TXT)",
            data=resultado_txt,
            file_name="plano_corte.txt",
            mime="text/plain"
        )
    else:
        st.error("Nenhuma solução encontrada!")
