#!/usr/env/python3
# -*- coding: utf-8 -*-

#import numpy as np
#import scipy.stats as spst
import pandas as pd
import os.path
import datetime as dt
import seaborn as sns
#import pymc3 as pm
import matplotlib.pyplot as plt
from matplotlib.ticker import LogFormatterSciNotation

sns.set(style = 'ticks', rc = { 'grid.color': '.8', 'grid.linestyle': '-'})

# ##
# parâmetros
# ##
mm_periodo = 5


# classe para enganar o formatador com notação científica.
class CustomTicker(LogFormatterSciNotation):
    def __call__(self, x, pos=None):
        return "{x:g}".format(x=x)

# leitura dos dados

DATAFILE = r'HIST_PAINEL_COVIDBR_'

today = dt.date.today()
last_day = today + dt.timedelta(days = -1)

DATAFILE_DATE = DATAFILE + dt.date.strftime(last_day, "%Y%m%d") + r'.xlsx'
DATAFILE_DATA_io = os.path.join(r'.', DATAFILE_DATE)

covidbr = pd.read_excel(DATAFILE_DATA_io)

# pré-processamento dos dados

covidbr['data'] = pd.to_datetime(covidbr['data'], format='%Y-%m-%d')

# ##
# transformação dos dados
# ##

mask_exc_resumo = ~covidbr['municipio'].isnull()

interessante = ['regiao', 'estado', 'municipio', 'data', 'dias_caso_0',
                'obitosAcumulado', 'casosAcumulado', 'obitosNovo', 'casosNovo',
                'obitosMMhab', 'casosMMhab', 'obitosAcumMMhab', 'casosAcumMMhab']

agrupar_full = ['estado', 'municipio']
agrupar_estado = ['estado']
agrupar_regiao = ['regiao']

# dados em que a contaminação ocorreu fora de um município:
# substituir o nome do município de NaN para 'SEM MUNICÍPIO'

# resumo por estado: substituir o nome do município de NaN para 'RESUMO'

# resumo Brasil: substituir os nomes do munícipio e do estado de NaN para 'Brasil'

mask_forademunicipios = (covidbr['municipio'].isnull() & ~covidbr['codmun'].isnull())
mask_resumo_estado = (covidbr['municipio'].isnull() & covidbr['codmun'].isnull())
mask_resumo_brasil = (covidbr['estado'].isnull())

covidbr.loc[covidbr[mask_forademunicipios].index, 'municipio'] = 'SEM MUNICÍPIO'
covidbr.loc[covidbr[mask_resumo_estado].index, 'municipio'] = 'RESUMO'
covidbr.loc[covidbr[mask_resumo_brasil].index, 'municipio'] = 'Brasil'
covidbr.loc[covidbr[mask_resumo_brasil].index, 'estado'] = 'Brasil'

# data para dias desde o 1o caso

covidbr['dias_caso_0'] = covidbr['data'] - covidbr['data'].iloc[0]
covidbr['dias_caso_0'] = covidbr['dias_caso_0'].apply(lambda x: getattr(x, 'days')).astype(int)

# casos diários a partir de casos acumulados (idem para obitos)

covidbr['obitosNovo'] = covidbr.groupby(agrupar_full)['obitosAcumulado'].diff().fillna(0)
covidbr['casosNovo'] = covidbr.groupby(agrupar_full)['casosAcumulado'].diff().fillna(0)

# casos e óbitos na última semana

covidbr['obitos_7d'] = covidbr.groupby(agrupar_full)['obitosAcumulado'].diff(7).fillna(0)
covidbr['casos_7d'] = covidbr.groupby(agrupar_full)['casosAcumulado'].diff(7).fillna(0)

# casos e obitos por milhão de habitantes

covidbr['obitosMMhab'] = covidbr['obitosNovo'] / (covidbr['populacaoTCU2019']/(10**6))
covidbr['casosMMhab'] = covidbr['casosNovo'] / (covidbr['populacaoTCU2019']/(10**6))

covidbr['obitosAcumMMhab'] = covidbr['obitosAcumulado'] / (covidbr['populacaoTCU2019']/(10**6))
covidbr['casosAcumMMhab'] = covidbr['casosAcumulado'] / (covidbr['populacaoTCU2019']/(10**6))

covidbr['obitos_7d_MMhab'] = covidbr['obitos_7d'] / (covidbr['populacaoTCU2019']/(10**6))
covidbr['casos_7d_MMhab'] = covidbr['casos_7d'] / (covidbr['populacaoTCU2019']/(10**6))

# suavização: média móvel

mm_aplicar = ['obitosAcumMMhab', 'obitos_7d_MMhab', 'casosAcumMMhab', 'casos_7d_MMhab']
for mm in mm_aplicar:
    covidbr[mm + '_mm'] = covidbr.groupby(agrupar_full)[mm].apply(lambda x: x.rolling(mm_periodo).mean())

# data para dias desde 0.1 obito por MM hab

mask_obitoMMhab = covidbr['obitosAcumMMhab'] >= 0.1

covidrel = covidbr.loc[mask_obitoMMhab,:]

covidrel['dias_desde_obito_MMhab'] = covidrel.groupby(agrupar_full)['data'].apply(lambda x:x-x.iloc[0])
covidrel['dias_desde_obito_MMhab'] = covidrel['dias_desde_obito_MMhab'].apply(lambda x: x.days).astype(int)

# ##
# pos-processamento
# ##

# grafico obitos acumulados por MM hab(log) x novos obitos na ultima semana por MM hab (log)
plt.figure()
ax1o = sns.lineplot(data = covidrel[~mask_exc_resumo][covidrel['estado'].isin(['RJ', 'SP', 'AM', 'RS', 'Brasil'])],
                  x = 'obitosAcumMMhab_mm', y = 'obitos_7d_MMhab_mm', hue='estado',
                  err_style=None)
plt.tight_layout()
sns.despine()

plt.figure()
ax2o = sns.lineplot(data = covidrel[covidrel['municipio'].isin(
                        ['Niterói', 'Rio de Janeiro', 'São Paulo', 'Brasil', 'Manaus']
                    )],
                  x='obitosAcumMMhab_mm', y='obitos_7d_MMhab_mm', hue='municipio',
                  err_style=None)
plt.tight_layout()
sns.despine()

ax1c = sns.lineplot(data = covidrel[~mask_exc_resumo][covidrel['estado'].isin(['RJ', 'SP', 'AM', 'RS', 'Brasil'])],
                  x = 'casosAcumMMhab_mm', y = 'casos_7d_MMhab_mm', hue='estado',
                  err_style=None)
plt.tight_layout()
sns.despine()

plt.figure()
ax2c = sns.lineplot(data = covidrel[covidrel['municipio'].isin(
                        ['Niterói', 'Rio de Janeiro', 'São Paulo', 'Brasil', 'Manaus']
                    )],
                  x='casosAcumMMhab_mm', y='casos_7d_MMhab_mm', hue='municipio',
                  err_style=None)
plt.tight_layout()
sns.despine()

# grafico dias desde 0.1 obito por MM hab. x obitos acumulados por MM hab. (log)
plt.figure()
ax3o = sns.lineplot(data = covidrel[~mask_exc_resumo][covidrel['estado'].isin(['RJ', 'SP', 'AM', 'RS', 'Brasil'])],
                  x = 'dias_desde_obito_MMhab', y = 'obitosAcumMMhab_mm', hue='estado',
                  err_style=None)
plt.tight_layout()
sns.despine()

plt.figure()
ax4o = sns.lineplot(data = covidrel[covidrel['municipio'].isin(
                        ['Niterói', 'Rio de Janeiro', 'São Paulo', 'Brasil', 'Manaus']
                    )],
                  x = 'dias_desde_obito_MMhab', y = 'obitosAcumMMhab_mm', hue='municipio',
                  err_style=None)
plt.tight_layout()
sns.despine()

plt.figure()
ax3c = sns.lineplot(data = covidrel[~mask_exc_resumo][covidrel['estado'].isin(['RJ', 'SP', 'AM', 'RS', 'Brasil'])],
                  x = 'dias_desde_obito_MMhab', y = 'casosAcumMMhab_mm', hue='estado',
                  err_style=None)
plt.tight_layout()
sns.despine()

plt.figure()
ax4c = sns.lineplot(data = covidrel[covidrel['municipio'].isin(
                        ['Niterói', 'Rio de Janeiro', 'São Paulo', 'Brasil', 'Manaus']
                    )],
                  x = 'dias_desde_obito_MMhab', y = 'casosAcumMMhab_mm', hue='municipio',
                  err_style=None)
plt.tight_layout()
sns.despine()


for ax in [ax1o, ax2o]:
    ax.set(xscale = 'log', yscale = 'log',
           xticks = {'minor': True}, yticks = {'minor': True},
           adjustable = 'datalim',
           xlabel = 'Óbitos Totais (por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
           ylabel = 'Novos Óbitos (últ. 7 dias, por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
           title = 'Evolução da COVID-19 no Brasil (Óbitos)')

    ax.get_yaxis().set_major_formatter(CustomTicker())
    ax.get_xaxis().set_major_formatter(CustomTicker())

for ax in [ax1c, ax2c]:
    ax.set(xscale = 'log', yscale = 'log',
           xticks = {'minor': True}, yticks = {'minor': True},
           adjustable = 'datalim',
           xlabel = 'Casos Totais (por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
           ylabel = 'Novos Casos (últ. 7 dias, por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
           title = 'Evolução da COVID-19 no Brasil (Infecções)')

    ax.get_yaxis().set_major_formatter(CustomTicker())
    ax.get_xaxis().set_major_formatter(CustomTicker())

for ax in [ax3o, ax4o]:
    ax.set(xscale = 'linear', yscale = 'log',
           xticks={'minor': True}, yticks={'minor': True},
           adjustable = 'datalim',
           xlabel = 'Dias desde 0.1 óbito por MM hab.', ylabel = 'Óbitos Totais (por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
           title = 'Evolução da COVID-19 no Brasil (Óbitos)')
    ax.get_yaxis().set_major_formatter(CustomTicker())

for ax in [ax3c, ax4c]:
    ax.set(xscale = 'linear', yscale = 'log',
           xticks={'minor': True}, yticks={'minor': True},
           adjustable = 'datalim',
           xlabel = 'Dias desde 0.1 óbito por MM hab.', ylabel = 'Casos Totais (por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
           title = 'Evolução da COVID-19 no Brasil (Infecções)')
    ax.get_yaxis().set_major_formatter(CustomTicker())