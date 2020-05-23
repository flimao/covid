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

fig = px.line(df, x='dias_desde_obito_MMhab', y='casos_7d_MMhab', color='estado',
              log_y = True, hover_name='estado')

fig.update_traces(connectgaps = True,
                  hovertemplate=
                  '<b>%{y:.1f} casos novos</b> / MM hab. nos 7 dias anteriores'
                  )

fig.update_layout(hovermode='x unified')

fig.update_yaxes(title_text = 'Casos novos (últimos 7 dias, por MM hab., média móvel de ' + str(mm_periodo) + ' dias)')
fig.update_xaxes(title_text = 'Dias desde óbitos = 0,1 / MM hab.')

log_or_linear = [{
    'active': 0,
    'buttons':[
        { 'label': 'Log Scale',
          'method': 'update',
          'args': [{'visible': [True, True]},
                   {'title': 'Evolução da COVID-19 no Brasil (Infecções) (escala log)',
                    'yaxis':
                        {'type': 'log',
                         'title':{'text': 'Casos novos (últimos 7 dias, por MM hab., média móvel de '
                                          + str(mm_periodo) + ' dias)'}
                         }
                    }]
        },
        { 'label': 'Linear Scale',
          'method': 'update',
          'args': [{'visible': [True, True]},
                   {'title': 'Evolução da COVID-19 no Brasil (Infecções) (escala linear)',
                    'yaxis':
                        {'type': 'linear',
                         'title':{'text': 'Casos novos (últimos 7 dias, por MM hab., média móvel de '
                                          + str(mm_periodo) + ' dias)'}
                         }
                    }]
        }]
}]

fig.update_layout({'updatemenus': log_or_linear})

fig.write_html(html)
fig.write_image(img)
