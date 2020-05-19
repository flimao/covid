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

sns.set(style = 'ticks', rc = { 'grid.color': '.8', 'grid.linestyle': '-'})
locale.setlocale(locale.LC_ALL,'portuguese_brazil')

# ##
# parâmetros
# ##
mm_periodo = 5


# classe para enganar o formatador com notação científica.
class CustomTicker(LogFormatterSciNotation):
    def __call__(self, x, pos=None):
        return "{x:g}".format(x=x)


class covid_brasil:
    """
    classe para leitura, processamento e pós-processamento dos dados brasileiros
    da COVID-19
    """
    def __init__(self, diretorio = None):

        # se diretorio for None, corresponde ao diretorio raiz do script

        if diretorio is None:
            diretorio = r'..'

        self.covidbr = self.ler_dados(diretorio)
        self.preproc()
        self.transform()


    def ler_dados(self, diretorio):
        """
        ler os dados da planilha excel exposta diariamente por https://covid.saude.gov.br/

        :param diretorio: o diretório contendo o arquivo excel
        :return: um dataframe contendo as informações do arquivo excel
        """

        DATAFILE = r'HIST_PAINEL_COVIDBR_'

        today = dt.date.today()
        last_day = today + dt.timedelta(days = -1)

        DATAFILE_DATE = DATAFILE + dt.date.strftime(last_day, "%d%b%Y") + r'.xlsx'
        DATAFILE_DATA_io = os.path.join(diretorio, r'data', r'Brasil', DATAFILE_DATE)

        return pd.read_excel(DATAFILE_DATA_io)


    def preproc(self):
        """
        pre-processamento dos dados
        :return: None
        """

        self.covidbr['data'] = pd.to_datetime(self.covidbr['data'], format='%Y-%m-%d')


    def transform(self):
        """
        transformação dos dados. Engloba várias transformações
        :return: None
        """

        # definição de constantes
        self.mask_exc_resumo = ~self.covidbr['municipio'].isnull()

        self.interessante = ['regiao', 'estado', 'municipio', 'data', 'dias_caso_0',
                             'obitosAcumulado', 'casosAcumulado', 'obitosNovo', 'casosNovo',
                             'obitosMMhab', 'casosMMhab', 'obitosAcumMMhab', 'casosAcumMMhab']

        self.agrupar_full = ['estado', 'municipio']
        self.agrupar_estado = ['estado']
        self.agrupar_regiao = ['regiao']

        # transformações
        self.substituir_nomes()
        self.dias_desde_caso_0()
        self.casos_obitos_novos()
        self.casos_obitos_ultima_semana()
        self.casos_obitos_percapita()
        self.suavizacao()


    def substituir_nomes(self):
        """
        substituir nomes relevantes:
            dados em que a contaminação ocorreu fora de um município:
            substituir o nome do município de NaN para 'SEM MUNICÍPIO'

            resumo por estado: substituir o nome do município de NaN para 'RESUMO'

            resumo Brasil: substituir os nomes do munícipio e do estado de NaN para 'Brasil'

        :return: None
        """

        mask_forademunicipios = (self.covidbr['municipio'].isnull() & ~self.covidbr['codmun'].isnull())
        mask_resumo_estado = (self.covidbr['municipio'].isnull() & self.covidbr['codmun'].isnull())
        mask_resumo_brasil = (self.covidbr['estado'].isnull())

        self.covidbr.loc[self.covidbr[mask_forademunicipios].index, 'municipio'] = 'SEM MUNICÍPIO'
        self.covidbr.loc[self.covidbr[mask_resumo_estado].index, 'municipio'] = 'RESUMO'
        self.covidbr.loc[self.covidbr[mask_resumo_brasil].index, 'municipio'] = 'Brasil'
        self.covidbr.loc[self.covidbr[mask_resumo_brasil].index, 'estado'] = 'Brasil'


    def dias_desde_caso_0(self):
        """
        calcular dias desde caso 0
        :return: None
        """

        self.covidbr['dias_caso_0'] = self.covidbr['data'] - self.covidbr['data'].iloc[0]
        self.covidbr['dias_caso_0'] = self.covidbr['dias_caso_0'].apply(lambda x: x.days).astype(int)


    def casos_obitos_novos(self):
        """
        casos diários a partir de casos acumulados (idem para obitos)
        :return: None
        """

        self.covidbr['obitosNovo'] = self.covidbr.groupby(self.agrupar_full)['obitosAcumulado'].diff().fillna(0)
        self.covidbr['casosNovo'] = self.covidbr.groupby(self.agrupar_full)['casosAcumulado'].diff().fillna(0)


    def casos_obitos_ultima_semana(self):
        """
        casos e óbitos na última semana
        :return: None
        """

        self.covidbr['obitos_7d'] = self.covidbr.groupby(self.agrupar_full)['obitosAcumulado'].diff(7).fillna(0)
        self.covidbr['casos_7d'] = self.covidbr.groupby(self.agrupar_full)['casosAcumulado'].diff(7).fillna(0)


    def casos_obitos_percapita(self):
        """
        casos e óbitos por milhão de habitantes
        :return: None
        """

        self.covidbr['obitosMMhab'] = self.covidbr['obitosNovo'] / (self.covidbr['populacaoTCU2019'] / (10 ** 6))
        self.covidbr['casosMMhab'] = self.covidbr['casosNovo'] / (self.covidbr['populacaoTCU2019'] / (10 ** 6))

        self.covidbr['obitosAcumMMhab'] = self.covidbr['obitosAcumulado'] /\
                                          (self.covidbr['populacaoTCU2019'] / (10 ** 6))
        self.covidbr['casosAcumMMhab'] = self.covidbr['casosAcumulado'] / (self.covidbr['populacaoTCU2019'] / (10 ** 6))

        self.covidbr['obitos_7d_MMhab'] = self.covidbr['obitos_7d'] / (self.covidbr['populacaoTCU2019'] / (10 ** 6))
        self.covidbr['casos_7d_MMhab'] = self.covidbr['casos_7d'] / (self.covidbr['populacaoTCU2019'] / (10 ** 6))


    def suavizacao(self):
        """
        suavização via média móvel com período definido anteriormente
        :return: None
        """

        mm_aplicar = ['obitosAcumMMhab', 'obitos_7d_MMhab', 'casosAcumMMhab', 'casos_7d_MMhab']
        for mm in mm_aplicar:
            self.covidbr[mm + '_mm'] = self.covidbr.groupby(self.agrupar_full)[mm].apply(
                lambda x: x.rolling(mm_periodo).mean()
            )

    def dias_desde_obito_percapita(self):
        """
        cálculo de # de dias desde 0.1 obito por MM hab
        :return: None
        """
        self.mask_obitoMMhab = self.covidbr['obitosAcumMMhab'] >= 0.1

        self.covidrel = self.covidbr.loc[mask_obitoMMhab, :]

        self.covidrel['dias_desde_obito_MMhab'] = self.covidrel.groupby(self.agrupar_full)['data'].apply(
            lambda x: x - x.iloc[0]
        )

        self.covidrel['dias_desde_obito_MMhab'] = self.covidrel['dias_desde_obito_MMhab'].apply(
            lambda x: x.days
        ).astype(int)


br = covid_brasil(diretorio = None)
covidrel = br.covidrel


# ##
# pos-processamento
# ##

# grafico obitos acumulados por MM hab(log) x novos obitos na ultima semana por MM hab (log)
plt.figure()
ax1o = sns.lineplot(data = covidrel[~br.mask_exc_resumo][covidrel['estado'].isin(['RJ', 'SP', 'AM', 'RS', 'Brasil'])],
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

ax1c = sns.lineplot(data = covidrel[~br.mask_exc_resumo][covidrel['estado'].isin(['RJ', 'SP', 'AM', 'RS', 'Brasil'])],
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