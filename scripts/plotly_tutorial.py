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
normalizacao = ['percapita']

br = covid.covid_brasil(diretorio = None, graficos = False)
df = br.covidrel[(~br.mask_exc_resumo_rel)&(br.covidrel['estado'].isin(data_estados))]

df_norm, titulo_x, titulo_y = br.norm_grafico(
    dados=df,
    normalizacao=normalizacao,
    x_orig='dias_desde_obito_MMhab',
    y_orig='obitos_7d_mm',
    titulo_x_orig='Dias desde óbitos = 0,1 / MM hab.',
    titulo_y_orig='Novos Óbitos (últ. 7 dias, média móvel de ' + str(mm_periodo) + ' dias)',
    norm_xy='y', crlf='<br>', plotly=True
)

html = r'..\imgs (nogit)\img.html'
img = r'..\imgs (nogit)\img.png'

fig1 = px.line(df_norm, x='x', y='y', color='estado', log_y = True, hover_name='estado')

#fig2 = px.line(df, x='dias_desde_obito_MMhab', y='obitos_7d_MMhab', color='estado',
#              log_y = True, hover_name='estado')
fig = fig1 # + fig2

fig.update_traces(connectgaps = True,
                  hovertemplate=
                  '<b>%{y:.1f} casos novos</b> / MM hab. nos 7 dias anteriores'
                  )

fig.update_layout(hovermode='x unified',
                  title_text = 'Evolução da COVID-19 no Brasil (Óbitos)')

fig.update_yaxes(title_text = titulo_y)
fig.update_xaxes(title_text = titulo_x)

log_linear = [{
    'active': 0,
    'y': 0.96, 'x': -0.11,
    'xanchor': 'right', 'yanchor':'top',
    'type': 'dropdown',
    'buttons':[
        { 'label': 'Log',
          'method': 'relayout',
          'args': ['yaxis', {'type': 'log',
                             'title': {'text': titulo_y }}]
        },
        { 'label': 'Linear',
          'method': 'relayout',
          'args': ['yaxis', {'type': 'linear',
                             'title': {'text': titulo_y }}]
        }
]
},{
    'active': 1,
    'y': -0.16, 'x': 0.9,
    'xanchor': 'left', 'yanchor':'top',
    'type': 'dropdown', 'direction': 'left',
    'buttons':[
        { 'label': 'Log',
          'method': 'relayout',
          'args': ['xaxis', {'type': 'log',
                             'title': {'text': titulo_x }}]
        },
        { 'label': 'Linear',
          'method': 'relayout',
          'args': ['xaxis', {'type': 'linear',
                             'title': {'text': titulo_x }}]
        }
]
}]

annot_log_linear = [
    dict(text="Escala", showarrow=False,
         x=-0.11, y=0.96, yref="paper", xref='paper',
         xanchor='right', yanchor='bottom',
        font_size=16
         ),
    dict(text="Escala", showarrow=False,
         x=0.9, y=-0.17, yref="paper", xref='paper',
         xanchor='right', yanchor='top',
         font_size=16
         )
]

obitos_casos = [dict(
    active=0,
    x=0.5, y=1.1,
    xanchor='left', yanchor='top',
    type='dropdown', direction='down',
    buttons=[dict(
        label='óbitos',
        method='restyle',
        args=[{'x': [ df_norm[df_norm['estado'] == c].x for c in data_estados ],
               'y': [ df_norm[df_norm['estado'] == c].y for c in data_estados ]
               }]
    ), dict(
        label='casos',
        method='restyle',
        args=[{'x': [ df_norm[df_norm['estado'] == c].x for c in data_estados ],
               'y': [ df_norm[df_norm['estado'] == c].x for c in data_estados ]
               }]
    )
    ]
)]

annot_obitos_casos = [
    dict(text="Tipo", showarrow=False,
         x=0.5, y=1.09, yref="paper", xref='paper',
         xanchor='right', yanchor='top',
         font_size = 16
         )
]

total_novos = [dict(
    active=0,
    x=0.75, y=1.1,
    xanchor='left', yanchor='top',
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
         xanchor='right', yanchor='top',
         font_size = 16
         )
]

fig.update_layout(updatemenus=log_linear + obitos_casos + total_novos,
                  annotations=annot_log_linear + annot_obitos_casos + annot_total_novos)

fig.write_html(html)
fig.write_image(img)