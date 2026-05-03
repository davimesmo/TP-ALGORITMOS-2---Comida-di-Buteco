import dash_leaflet as dl
from dash_extensions.enrich import DashProxy
from dash_extensions.javascript import arrow_function
from dash import html, dcc, Input, Output, State, no_update
import duckdb as db
import pandas as pd
import time
import json
import requests
from kdtree import KdNode, KdTree
from boteco import Boteco
import csv
import math

con = db.connect()
resultados = con.execute("""
    SELECT * FROM read_csv('botecos_coordenadas.csv')
""").fetchall()

botecos = []
for quad in resultados:
    botecos.append(Boteco(quad[0], quad[1], quad[2], quad[3]))

arvore = KdTree()
arvore.insertAll(botecos)

app = DashProxy()
app.layout = html.Div([
    html.H1("Busca de Botecos - TP1", style={'textAlign': 'center'}),
    html.Div([
        html.Label("Endereço:"),
        dcc.Input(id='input-endereco', type='text', style={'width': '300px', 'marginRight': '10px', 'marginLeft': '10px'}),
        
        html.Label("Tamanho da Diagonal em km:"),
        dcc.Input(id='input-diagonal', type='number', style={'width': '80px', 'marginRight': '10px', 'marginLeft': '10px'}),

        html.Button('Buscar Botecos na Área', id='btn-buscar', n_clicks=0, style={'marginRight': '10px', 'marginLeft': '10px'})
    ], style={'padding': '20px', 'backgroundColor': '#f0f0f0', 'marginBottom': '20px'}),

    dl.Map(id='mapa-botecos', center=[-19.9166, -43.9344], zoom=12, style={"height": "50vh", 'width': '100%'}, children=[
        dl.TileLayer(),
        dl.GeoJSON(
            url="/assets/BAIRRO.json",
            id="camada-bairros",
            options=dict(style=dict(color="gray", weight=1, fillOpacity=0.05)), 
            hoverStyle=arrow_function(dict(weight=3, color="red", dashArray="")) 
        ),
        dl.LayerGroup(id='camada-pinos')
    ]),
    
    html.Div([
        html.H3("Resultados da Busca"),
        html.Div(id='tabela-resultados')
    ], style={'padding': '20px'})
])

def calcularLimites(centroLat, centroLon, diagonalKm):
    #https://teleco.com.br/tutoriais/tutorialsmsloc2/
    ladoKm = diagonalKm / math.sqrt(2)
    deltaKm = ladoKm / 2.0
    deltaLat = deltaKm / 111.32
    deltaLon = deltaKm / (111.32 * math.cos(math.radians(centroLat)))
    return {
        "minX": centroLon - deltaLon,
        "maxX": centroLon + deltaLon,
        "minY": centroLat - deltaLat,
        "maxY": centroLat + deltaLat
    }

def calcularDistancia(lat1, lon1, lat2, lon2):
    #https://www.movable-type.co.uk/scripts/latlong.html 
    R = 6371.0 
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.callback(
    Output("mapa-botecos", "viewport"), 
    Output("camada-pinos", "children"),
    Output("tabela-resultados", "children"),
    Input("btn-buscar", "n_clicks"),    
    State("input-endereco", "value"), 
    State("input-diagonal", "value"),  
    prevent_initial_call=True
)
def buscar_e_voar(n_clicks, endereco_digitado, diagonal_digitada):
    if not endereco_digitado:
        return no_update, no_update, no_update
    
    if diagonal_digitada is None:
        diagonal_digitada = 0
         
    url = "https://nominatim.openstreetmap.org/search"
    cabecalhos = {"User-Agent": "davi_ufmg"}
    parametros = {"q": f"{endereco_digitado}, Belo Horizonte, Minas Gerais", "format": "json"}
    retorno = requests.get(url, params=parametros, headers=cabecalhos)
    
    if retorno.status_code == 200:
        retorno = retorno.json()
        if len(retorno) > 0:
            centroLat = float(retorno[0]['lat'])
            centroLon = float(retorno[0]['lon'])
            comando_voo = dict(center=[centroLat, centroLon], zoom=15, transition="flyTo")
            desenhos_mapa = [
                dl.Marker(id= f"id{n_clicks}",position=[centroLat, centroLon], children=[dl.Tooltip(content=f"Você está <b>aqui</b>!<br>{endereco_digitado}")])
            ]
            tabela_html = html.Div()

            if diagonal_digitada > 0:
                fronteira = calcularLimites(centroLat, centroLon, diagonal_digitada)
                desenhos_mapa.append(dl.Polygon(
                    weight=2, color="blue", fillOpacity=0.1, interactive=False, 
                    positions=[[fronteira["maxY"], fronteira["minX"]],[fronteira["maxY"], fronteira["maxX"]], [fronteira["minY"], fronteira["maxX"]], [fronteira["minY"], fronteira["minX"]]
                    ]
                ))
                
                botecosNaArea = []
                arvore.search(fronteira["minX"], fronteira["maxX"], fronteira["minY"], fronteira["maxY"], botecosNaArea, 0, arvore.raiz)
                
                if len(botecosNaArea) > 0: 
                    lista_ordenada = []
                    for b in botecosNaArea:
                        dist = calcularDistancia(centroLat, centroLon, b.lat, b.lon)
                        lista_ordenada.append({"boteco": b, "distancia": dist})
                    
                    lista_ordenada.sort(key=lambda item: item["distancia"])
                    linhas_tabela = []
                    icone_verde = dict(
                        iconUrl='https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
                        shadowUrl='https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                        iconSize=[25, 41],
                        iconAnchor=[12, 41],
                        popupAnchor=[1, -34],
                        shadowSize=[41, 41]
                    )
                    for item in lista_ordenada:
                        b = item["boteco"]
                        d = item["distancia"]
                        desenhos_mapa.append(
                            dl.Marker(position=[b.lat, b.lon], icon=icone_verde,children=[dl.Tooltip(content=f"<b>{b.nome}</b><br>{b.endereco}<br>Distância: {d:.2f} km")])
                        )
                        linhas_tabela.append(html.Tr([
                            html.Td(b.nome, style={'padding': '8px', 'borderBottom': '1px solid #ddd'}),
                            html.Td(f"{d:.2f} km", style={'padding': '8px', 'borderBottom': '1px solid #ddd', 'color': 'green'})
                        ]))
                        
                    tabela_html = html.Table([
                        html.Thead(html.Tr([
                            html.Th("Nome do Bar", style={'textAlign': 'left', 'padding': '8px', 'backgroundColor': '#f2f2f2'}),
                            html.Th("Distância", style={'textAlign': 'left', 'padding': '8px', 'backgroundColor': '#f2f2f2'})
                        ])),
                        html.Tbody(linhas_tabela)
                    ], style={'width': '100%', 'borderCollapse': 'collapse'})
                    
            return comando_voo, desenhos_mapa, tabela_html                                                                          
    else: 
        print(f"Erro HTTP {retorno.status_code}")
        
    return no_update, no_update, no_update

if __name__ == "__main__":
    app.run()