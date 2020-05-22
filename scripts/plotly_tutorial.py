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


# classe para enganar o formatador com notação científica.

br = covid.covid_brasil(diretorio = None)
df = br.covidrel[br.covidrel['municipio'].isin(['Niterói', 'Rio de Janeiro', 'São Paulo', 'Brasil'])]

html = r'..\imgs (nogit)\img.html'
img = r'..\imgs (nogit)\img.png'

fig = px.line(df, x='dias_desde_obito_MMhab', y='casos_7d_MMhab', color='municipio')
fig.update_yaxes({'title':
    {'text': 'Casos novos (últimos 7 dias, por MM hab., média móvel de ' + str(mm_periodo) + ' dias)'}})
fig.update_xaxes({'title': {'text': 'Dias desde óbitos = 0,1 / MM hab.'}})

fig.write_html(html)
fig.write_image(img)
