#!/usr/env/python3
# -*- coding: utf-8 -*-

#import numpy as np
#import scipy.stats as spst
import pandas as pd
import os.path
import datetime as dt
import locale
import seaborn as sns
#import pymc3 as pm
import matplotlib.pyplot as plt
from matplotlib.ticker import LogFormatterSciNotation

import plotly.graph_objs as go
import plotly.express as px
import dash
import dash_core_components as dcc
import dash_html_components as html

from thesmuggler import smuggle

covid = smuggle('./covid.py')

sns.set(style = 'ticks', rc = { 'grid.color': '.8', 'grid.linestyle': '-'})
locale.setlocale(locale.LC_ALL,'portuguese_brazil')

# ##
# parâmetros
# ##
mm_periodo = 5

#data_estados = ['AM', 'SP', 'RJ', 'Brasil']
data_estados = ['Brasil', 'RJ']
data_municipios = ['Brasil', 'Niterói', 'Rio de Janeiro']
normalizacao = ['percapita']

br = covid.covid_brasil(diretorio = None, graficos = False)
df = br.covidrel[(~br.mask_exc_resumo_rel)&(br.covidrel['estado'].isin(data_estados))]
df_est = br.covidrel[br.mask_exc_resumo_rel]
df_estunq = df_est.groupby('coduf')['estado'].first()

df_mun = br.covidrel[br.mask_exc_resumo_rel]
df_mununq = df_mun.groupby('codmun')[['estado', 'municipio']].first()

df_norm, titulo, _ = br.norm_grafico(
    dados=df,
    normalizacao=normalizacao,
    x_orig='dias_desde_obito_MMhab',
    y_orig='obitos_7d_mm',
    titulo_x_orig='Dias desde óbitos = 0,1 / MM hab.',
    titulo_y_orig='Novos Óbitos (últ. 7 dias, média móvel de ' + str(mm_periodo) + ' dias)',
    norm_xy='y', crlf='<br>', plotly=True
)

html_fig = r'..\imgs (nogit)\img.html'
img = r'..\imgs (nogit)\img.png'

fig1 = px.line(df_norm, x='x_ott', y='y_ott', color='estado', log_y = True, hover_name='estado')

#fig2 = px.line(df, x='dias_desde_obito_MMhab', y='obitos_7d_MMhab', color='estado',
#              log_y = True, hover_name='estado')
fig = fig1 # + fig2

fig.update_traces(connectgaps = True,
                  hovertemplate=
                  '<b>%{y:.1f} casos novos</b> / MM hab. nos 7 dias anteriores'
                  )

fig.update_layout(hovermode='x unified',
                  title_text = 'Evolução da COVID-19 no Brasil (Óbitos)')

fig.update_yaxes(title_text = titulo['y_ont'])
fig.update_xaxes(title_text = titulo['x_ont'])

log_linear = [{
    'active': 0,
    'y': 1, 'x': 0,
    'xanchor': 'left', 'yanchor':'top',
    'type': 'dropdown',
    'buttons':[
        { 'label': 'Log',
          'method': 'relayout',
          'args': ['yaxis', {'type': 'log',
                             'title': {'text': titulo['y_ont'] }}]
        },
        { 'label': 'Linear',
          'method': 'relayout',
          'args': ['yaxis', {'type': 'linear',
                             'title': {'text': titulo['y_ont'] }}]
        }
]
},{
    'active': 1,
    'y': 0, 'x': 1,
    'xanchor': 'right', 'yanchor':'bottom',
    'type': 'dropdown', 'direction': 'left',
    'buttons':[
        { 'label': 'Log',
          'method': 'relayout',
          'args': ['xaxis', {'type': 'log',
                             'title': {'text': titulo['x_ont'] }}]
        },
        { 'label': 'Linear',
          'method': 'relayout',
          'args': ['xaxis', {'type': 'linear',
                             'title': {'text': titulo['x_ont'] }}]
        }
]
}]

obitos_casos = [dict(
    active=0,
    x=0.5, y=1.1,
    xanchor='left', yanchor='bottom',
    type='dropdown', direction='down',
    buttons=[dict(
        label='óbitos',
        method='restyle',
        args=[{'x': [ df_norm[df_norm['estado'] == c].x_ott for c in data_estados ],
               'y': [ df_norm[df_norm['estado'] == c].y_ott for c in data_estados ]
               }]
    ), dict(
        label='casos',
        method='restyle',
        args=[{'x': [ df_norm[df_norm['estado'] == c].x_ctt for c in data_estados ],
               'y': [ df_norm[df_norm['estado'] == c].y_ctt for c in data_estados ],
               'xaxis':{'title':{'text': titulo['x_cnt']}},
               'yaxis':{'title':{'text': titulo['y_cnt']}},
        }]
    )
    ]
)]

annot_obitos_casos = [
    dict(text="Tipo", showarrow=False,
         x=0.5, y=1.09, yref="paper", xref='paper',
         xanchor='right', yanchor='bottom',
         font_size = 16
         )
]

total_novos = [dict(
    active=0,
    x=0.75, y=1.1,
    xanchor='left', yanchor='bottom',
    type='dropdown', direction='down',
    buttons=[dict(
        label='# total',
        method='restyle',
        args=[]
    ), dict(
        label='# novos',
        method='restyle',
        args=[]
    )
    ]
)]

annot_total_novos = [
    dict(text="Concentração", showarrow=False,
         x=0.75, y=1.09, yref="paper", xref='paper',
         xanchor='right', yanchor='bottom',
         font_size = 16
         )
]

fig.update_layout(updatemenus=log_linear# + obitos_casos + total_novos,
                  #annotations=annot_obitos_casos + annot_total_novos)
                  )
fig.write_html(html_fig)
fig.write_image(img)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
    html.H1(children='Evolução da COVID-19 no Brasil'),

    html.Div(children='''
        Uma análise de dados da COVID-19 do Brasil e do mundo.
        \n\n\n        
    '''),

    dcc.Graph(
        id='covid',
        figure=fig
    ),

    html.Div(children=[

        html.Label('Municípios'),
        dcc.Dropdown(
            options=[
                {'label': df_mununq.loc[codmun, 'municipio'] + ', ' + df_mununq.loc[codmun, 'estado'], 'value': codmun}
                for codmun in df_mununq.index
            ],
            value=[330330, 330445],
            multi=True
        ),

        html.Label('Estados'),
        dcc.Dropdown(
            options=[
                {'label': df_estunq[coduf], 'value': coduf} for coduf in df_estunq.index
            ],
            value=[33, 34, 76],
            multi=True
        ),

        html.Label('Suavização'),
        dcc.RadioItems(
            options=[
                {'label': 'Sem suavização', 'value': 0},
                {'label': 'Média móvel de 7 dias', 'value': 7},
                {'label': 'Média móvel de 3 dias', 'value': 3},
                {'label': 'Outra média móvel', 'value': -1}
            ],
            value=7
        ),
        dcc.Input(value=5, type='number'),
    ], style={'columnCount': 2})
])

if __name__ == '__main__':
    app.run_server(debug=True)