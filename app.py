import streamlit as st
import pandas as pd
from itertools import combinations_with_replacement
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, PULP_CBC_CMD

# Configuração inicial
def encontra_combinacoes_possiveis(larguras_slitters, largura_bobina):
    combinacoes = []
    for n in range(1, largura_bobina // min(larguras_slitters) + 1):
        for combinacao in combinations_with_replacement(larguras_slitters, n):
            if sum(combinacao) == largura_bobina:
                combinacoes.append(combinacao)
    return combinacoes

def resolver_problema_corte(larguras_slitters, largura_bobina, peso_bobina, demandas, limite_inferior, limite_superior):
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
            pesos_por_largura = [largura * proporcao for largura in combinacao]
            combinacao_com_pesos = [f"{largura} | {round(peso, 2)} kg" for largura, peso in zip(combinacao, pesos_por_largura)]
            puxada = 2 if any(peso > 5000 for peso in pesos_por_largura) else 1
            resultado.append({
                "Plano de Corte": combinacao_com_pesos,
                "Quantidade": int(x[i].varValue),
                "Largura Total": sum(combinacao),
                "Puxada": puxada,
            })
    
    return pd.DataFrame(resultado)

def gerar_tabela_final(resultado, demandas, proporcao, produtos):
    pesos_totais = {demanda["width"]: 0 for demanda in demandas}
    
    for _, linha in resultado.iterrows():
        combinacao = linha["Plano de Corte"]
        quantidade = linha["Quantidade"]
        for item in combinacao:
            largura = int(item.split(" | ")[0])
            pesos_totais[largura] += quantidade * largura * proporcao
    
    tabela_final = []
    for demanda in demandas:
        largura = demanda["width"]
        peso_planejado = demanda["weight"]
        peso_total = pesos_totais.get(largura, 0)
        percentual_atendido = (peso_total / peso_planejado * 100) if peso_planejado > 0 else 0
        produto = produtos.get(largura, "Produto Desconhecido")
        tabela_final.append({
            "Largura (mm)": largura,
            "Produto": produto,
            "Demanda Planejada (kg)": peso_planejado,
            "Peso Total (kg)": peso_total,
            "Atendimento (%)": percentual_atendido,
        })
    
    return pd.DataFrame(tabela_final)

st.title("Otimização de Corte de Bobinas")

produtos = {
    105: "Perfil UDC Enrijecido 50x25x10x2,00x6000mm",
    170: "Perfil UDC Enrijecido 75x40x15x2,00x6000mm",
    197: "Perfil UDC Enrijecido 100x40x15x2,00x6000mm",
    219: "Perfil UDC Enrijecido 100x50x17x2,00x6000mm",
    244: "Perfil UDC Enrijecido 127x50x17x2,00x6000mm",
    264: "Perfil UDC Enrijecido 150x50x17x2,00x6000mm",
    295: "Perfil UDC Enrijecido 150x60x20x2,00x6000mm",
    375: "Perfil UDC Enrijecido 200x75x25x2,00x6000mm",
}

produto_selecionado = st.selectbox("Selecione o produto", list(produtos.keys()), format_func=lambda x: produtos[x])
peso_inserido = st.number_input("Digite o peso (kg)", min_value=1, step=1)
limite_inferior = st.number_input("Limite Inferior", min_value=0.01, max_value=1.0, value=0.90, step=0.01)
limite_superior = st.number_input("Limite Superior", min_value=1.0, max_value=2.0, value=1.30, step=0.01)

if st.button("Calcular Plano de Corte"):
    demands = [{"width": produto_selecionado, "weight": peso_inserido}]
    larguras_bobina = [1192, 1191, 1190, 1189, 1188]
    peso_bobina = 17715
    
    melhor_resultado = None
    melhor_largura = None
    
    for largura_bobina in larguras_bobina:
        resultado = resolver_problema_corte(list(produtos.keys()), largura_bobina, peso_bobina, demands, limite_inferior, limite_superior)
        if resultado is not None:
            if melhor_resultado is None or resultado["Quantidade"].sum() < melhor_resultado["Quantidade"].sum():
                melhor_resultado = resultado
                melhor_largura = largura_bobina
    
    if melhor_resultado is not None:
        proporcao = peso_bobina / melhor_largura
        tabela_final = gerar_tabela_final(melhor_resultado, demands, proporcao, produtos)
        st.write(f"### Melhor largura de bobina: {melhor_largura}")
        st.dataframe(melhor_resultado)
        st.write("### Tabela Final de Peso por Largura")
        st.dataframe(tabela_final)
    else:
        st.error("Nenhuma solução encontrada.")
