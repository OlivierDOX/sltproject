import streamlit as st
import pandas as pd
from itertools import combinations_with_replacement
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, PULP_CBC_CMD

# Configuração inicial
st.title("Otimização de Corte de Bobinas")

# Entrada do usuário para limites superior e inferior
limite_inferior = st.number_input("Limite Inferior (%)", min_value=0.0, max_value=2.0, value=0.90, step=0.01)
limite_superior = st.number_input("Limite Superior (%)", min_value=0.0, max_value=2.0, value=1.30, step=0.01)

# Lista de produtos
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

larguras_bobina = [1192, 1191, 1190, 1189, 1188]
peso_bobina = 17715

# Seleção de produtos pelo usuário
produtos_selecionados = st.multiselect("Selecione os produtos", options=list(produtos.keys()), format_func=lambda x: produtos[x])

demands = []
for prod in produtos_selecionados:
    peso = st.number_input(f"Peso para {produtos[prod]} (kg)", min_value=1, value=10000, step=1000)
    demands.append({"width": prod, "weight": peso})

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
            lpSum(x[i] * combinacao.count(largura) * proporcao * largura for i, combinacao in enumerate(combinacoes)) >= peso_necessario * limite_inferior,
            f"Atender_Minima_{largura}",
        )
        problema += (
            lpSum(x[i] * combinacao.count(largura) * proporcao * largura for i, combinacao in enumerate(combinacoes)) <= peso_necessario * limite_superior,
            f"Atender_Maxima_{largura}",
        )
    
    problema.solve(PULP_CBC_CMD(msg=False))
    
    if problema.status != 1:
        return None
    
    resultado = []
    for i, combinacao in enumerate(combinacoes):
        if x[i].varValue > 0:
            resultado.append({"Plano de Corte": combinacao, "Quantidade": int(x[i].varValue)})
    
    return pd.DataFrame(resultado)

if st.button("Calcular Plano de Corte"):
    melhor_resultado = None
    melhor_largura = None
    
    for largura_bobina in larguras_bobina:
        resultado = resolver_problema_corte(produtos_selecionados, largura_bobina, peso_bobina, demands)
        if resultado is not None:
            if melhor_resultado is None or resultado["Quantidade"].sum() < melhor_resultado["Quantidade"].sum():
                melhor_resultado = resultado
                melhor_largura = largura_bobina
    
    if melhor_resultado is not None:
        st.write(f"Melhor largura de bobina: {melhor_largura}")
        st.dataframe(melhor_resultado)
        
        # Criando arquivo para download
        txt_output = f"Melhor largura de bobina: {melhor_largura}\n\n"
        txt_output += melhor_resultado.to_string(index=False)
        st.download_button("Baixar resultado", txt_output, "resultado.txt")
    else:
        st.write("Nenhuma solução encontrada.")
