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
        self.graficos()

    def constantes(self):
        pass


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
        self.dias_desde_obito_percapita()

        # mais constantes
        self.mask_exc_resumo_rel = self.covidrel['municipio'].isnull()


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


    def suavizacao(self, janela_mm = mm_periodo):
        """
        suavização via média móvel com período definido anteriormente
        :return: None
        """

        mm_aplicar = ['obitosAcumMMhab', 'obitos_7d_MMhab', 'casosAcumMMhab', 'casos_7d_MMhab']
        mm_aplicado = [ mm + '_mm' for mm in mm_aplicar ]

        self.covidbr[mm_aplicado] = self.covidbr.groupby(self.agrupar_full)[mm_aplicar].apply(
            lambda x: x.rolling(janela_mm).mean()
        )


    def dias_desde_obito_percapita(self):
        """
        cálculo de # de dias desde 0.1 obito por MM hab
        :return: None
        """
        self.mask_obitoMMhab = self.covidbr['obitosAcumMMhab'] >= 0.1

        self.covidrel = self.covidbr.loc[self.covidbr[self.mask_obitoMMhab].index]

        self.covidrel['dias_desde_obito_MMhab'] = self.covidrel.groupby(self.agrupar_full)['data'].apply(
            lambda x: x - x.iloc[0]
        )

        self.covidrel['dias_desde_obito_MMhab'] = self.covidrel['dias_desde_obito_MMhab'].apply(
            lambda x: x.days
        ).astype(int)


    def graf_obitos_acum_por_novos_obitos_loglog(self, data_estados, data_municipios):
        """
        gráfico: óbitos acumulados por MM hab. (log) x novos óbitos na última semana por MM hab (log)
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municípios
        :return: objetos Axes
        """

        plt.figure()
        ax1o = sns.lineplot(
            data=data_estados, x='obitosAcumMMhab_mm', y='obitos_7d_MMhab_mm', hue='estado',
            err_style=None)
        plt.tight_layout()
        sns.despine()

        plt.figure()
        ax2o = sns.lineplot(data=data_municipios, x='obitosAcumMMhab_mm', y='obitos_7d_MMhab_mm', hue='municipio',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax1o, ax2o]

        for ax in axs:
            ax.set(xscale='log', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel='Total de Óbitos (por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
                   ylabel='Novos Óbitos (últ. 7 dias, por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
                   title='Evolução da COVID-19 no Brasil (Óbitos)')

            ax.get_yaxis().set_major_formatter(CustomTicker())
            ax.get_xaxis().set_major_formatter(CustomTicker())

        return axs


    def graf_casos_acum_por_novos_casos_loglog(self, data_estados, data_municipios):
        """
        gráfico: casos acumulados por MM hab. (log) x novos casos na última semana por MM hab (log)
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municípios
        :return: objetos Axes
        """

        plt.figure()
        ax1c = sns.lineplot(
            data=data_estados, x='casosAcumMMhab_mm', y='casos_7d_MMhab_mm', hue='estado',
            err_style=None)
        plt.tight_layout()
        sns.despine()

        plt.figure()
        ax2c = sns.lineplot(data=data_municipios, x='casosAcumMMhab_mm', y='casos_7d_MMhab_mm', hue='municipio',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax1c, ax2c]

        for ax in axs:
            ax.set(xscale='log', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel='Total de Casos (por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
                   ylabel='Novos Casos (últ. 7 dias, por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
                   title='Evolução da COVID-19 no Brasil (Infecções)')

            ax.get_yaxis().set_major_formatter(CustomTicker())
            ax.get_xaxis().set_major_formatter(CustomTicker())

        return axs


    def graf_obitos_acum_por_dias_pandemia_log(self, data_estados, data_municipios):
        """
        gráfico: data desde 0.1 óbito por MM hab. x óbitos acumulados por MM hab. (log)
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municípios
        :return:
        """
        plt.figure()
        ax3o = sns.lineplot(data=data_estados, x='dias_desde_obito_MMhab', y='obitosAcumMMhab_mm', hue='estado',
            err_style=None)
        plt.tight_layout()
        sns.despine()

        plt.figure()
        ax4o = sns.lineplot(data=data_municipios, x='dias_desde_obito_MMhab', y='obitosAcumMMhab_mm', hue='municipio',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax3o, ax4o]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel='Dias desde 0.1 óbito por MM hab.',
                   ylabel='Total de Óbitos (por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
                   title='Evolução da COVID-19 no Brasil (Óbitos)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs


    def graf_casos_acum_por_dias_pandemia_log(self, data_estados, data_municipios):
        """
        gráfico: data desde 0.1 óbito por MM hab. x casos acumulados por MM hab. (log)
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municípios
        :return:
        """

        plt.figure()
        ax3c = sns.lineplot(data=data_estados, x='dias_desde_obito_MMhab', y='casosAcumMMhab_mm', hue='estado',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        plt.figure()
        ax4c = sns.lineplot(data=data_municipios, x='dias_desde_obito_MMhab', y='casosAcumMMhab_mm', hue='municipio',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax3c, ax4c]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel='Dias desde 0.1 óbito por MM hab.',
                   ylabel='Total de Casos (por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
                   title='Evolução da COVID-19 no Brasil (Infecções)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs


    def graficos(self,
                 estados = ['RJ', 'SP', 'AM', 'RS', 'Brasil'],
                 municipios = ['Niterói', 'Rio de Janeiro', 'São Paulo', 'Brasil', 'Manaus']):
        """
        plotar gráficos
        :return: None
        """

        plt_data_estados = self.covidrel[~self.mask_exc_resumo_rel][self.covidrel['estado'].isin(estados)]
        plt_data_municipios = self.covidrel[self.covidrel['municipio'].isin(municipios)]

        # executar todas as funções no escopo atual começando por 'graf_'

        func_grafs = [ v for k,v in self.__class__.__dict__.items() if k.startswith('graf_') ]

        self.eixos = []

        for f in func_grafs:
            axs = f(self, plt_data_estados, plt_data_municipios)
            self.eixos += axs


br = covid_brasil(diretorio = None)