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

import covid

sns.set(style = 'ticks', rc = { 'grid.color': '.8', 'grid.linestyle': '-'})
locale.setlocale(locale.LC_ALL,'portuguese_brazil')

# ##
# parâmetros
# ##
mm_periodo = 5

data_estados = ['AM', 'SP', 'RJ', 'Brasil']

br = covid.covid_brasil(diretorio = None, graficos = False)
df = br.covidrel[(~br.mask_exc_resumo_rel)&(br.covidrel['estado'].isin(data_estados))]

html = r'..\imgs (nogit)\img.html'
img = r'..\imgs (nogit)\img.png'

y_axis_title = 'Casos novos (últimos 7 dias, por MM hab.)<br>' + \
               '(média móvel de ' + str(mm_periodo) + ' dias)'
x_axis_title = 'Dias desde óbitos = 0,1 / MM hab.'


fig1 = px.line(df, x='dias_desde_obito_MMhab', y='casos_7d_MMhab', color='estado',
              log_y = True, hover_name='estado')
#fig2 = px.line(df, x='dias_desde_obito_MMhab', y='obitos_7d_MMhab', color='estado',
              log_y = True, hover_name='estado')
#fig = fig1 + fig2

fig.update_traces(connectgaps = True,
                  hovertemplate=
                  '<b>%{y:.1f} casos novos</b> / MM hab. nos 7 dias anteriores'
                  )

fig.update_layout(hovermode='x unified',
                  title_text = 'Evolução da COVID-19 no Brasil (Infecções)')

fig.update_yaxes(title_text = y_axis_title)
fig.update_xaxes(title_text = x_axis_title)

log_or_linear = [{
    'active': 0,
    'y': 0.96, 'x': -0.11,
    'xanchor': 'right', 'yanchor':'top',
    'type': 'dropdown',
    'buttons':[
        { 'label': 'Log',
          'method': 'relayout',
          'args': ['yaxis', {'type': 'log',
                             'title': {'text': y_axis_title}}]
        },
        { 'label': 'Linear',
          'method': 'relayout',
          'args': ['yaxis', {'type': 'linear',
                             'title': {'text': y_axis_title}}]
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
                             'title': {'text': x_axis_title}}]
        },
        { 'label': 'Linear',
          'method': 'relayout',
          'args': ['xaxis', {'type': 'linear',
                             'title': {'text': x_axis_title}}]
        }
]
}]



annotations = [
        dict(text="Escala:", showarrow=False,
             x=-0.11, y=0.96, yref="paper", xref='paper',
             xanchor='right', yanchor='bottom'),
        dict(text="Escala:", showarrow=False,
             x=0.9, y=-0.17, yref="paper", xref='paper',
             xanchor='right', yanchor='top')
    ]

fig.update_layout(updatemenus=log_or_linear, annotations=annotations)

fig.write_html(html)
fig.write_image(img)
