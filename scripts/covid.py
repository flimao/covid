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
    def __init__(self, diretorio = None, graficos=True):

        # se diretorio for None, corresponde ao diretorio raiz do script

        if diretorio is None:
            diretorio = r'..'

        self.covidbr, self.areas, self.areas_estados = self.ler_dados(diretorio)
        self.check = [62810, 6810, 2011, 2014, 88, 0]
        self.preproc()
        self.transform()
        if graficos:
            self.graficos()

    def constantes(self):
        pass

    def ler_dados(self, diretorio):
        """
        ler os dados
            1) da planilha excel exposta diariamente por https://covid.saude.gov.br/
            2) de dados geográficos (áreas de municípios e estados) brasileiros

        :param diretorio: o diretório contendo os arquivos excel
        :return: dataframes contendo as informações dos arquivos excel
        """

        # dados da evolução da COVID-19
        DATAFILE = r'HIST_PAINEL_COVIDBR_'
        DATAFILE_GEO = r'AR_BR_RG_UF_RGINT_RGIM_MES_MIC_MUN_2019.xls'

        today = dt.date.today()
        last_day = today + dt.timedelta(days = -1)

        DATAFILE_DATE = DATAFILE + dt.date.strftime(last_day, "%d%b%Y") + r'.xlsx'
        DATAFILE_DATA_io = os.path.join(diretorio, r'data', r'Brasil', DATAFILE_DATE)

        covid = pd.read_excel(DATAFILE_DATA_io)

        # dados geográficos
        DATAFILE_GEO_io = os.path.join(diretorio, r'data', r'Brasil', DATAFILE_GEO)

        areas_mun = pd.read_excel(DATAFILE_GEO_io, sheet_name='AR_BR_MUN_2019')

        areas_estados = pd.read_excel(DATAFILE_GEO_io, sheet_name='AR_BR_UF_2019')

        return covid, areas_mun, areas_estados

    def preproc(self):
        """
        pre-processamento dos dados
        :return: None
        """

        # processar datas
        self.covidbr['data'] = pd.to_datetime(self.covidbr['data'], format='%Y-%m-%d')

        # deletar nomes que tenham valores NA
        # são valores no excel que estão fora das tabelas e que não tem relevância
        self.areas.dropna(inplace = True)
        self.areas_estados.dropna(inplace = True)

        # renomear colunas
        dict_rename_areas = {
            'CD_GCUF': 'coduf',
            'NM_UF': 'estado_nome',
            'NM_UF_SIGLA': 'estado',
            'CD_GCMUN': 'codmun',
            'NM_MUN_2019': 'municipio',
            'AR_MUN_2019': 'area'
        }

        dict_rename_areas_estados = {
            'CD_GCUF': 'coduf',
            'NM_UF': 'estado_nome',
            'NM_UF_SIGLA': 'estado',
            'AR_MUN_2019': 'area'
        }

        self.areas.rename(columns = dict_rename_areas, inplace = True)
        self.areas_estados.rename(columns = dict_rename_areas_estados, inplace = True)

        # acertar tipos das colunas
        self.areas[['coduf', 'codmun']] = self.areas[['coduf', 'codmun']].astype(int)
        self.areas_estados.coduf = self.areas_estados.coduf.astype(int)

        # trocar indice ID por indice (estado, municipio) ou estado
        self.areas.set_index(keys=['estado', 'municipio'], inplace=True)
        self.areas.drop(columns='ID', inplace=True)
        self.areas_estados.set_index(keys='estado', inplace=True)
        self.areas_estados.drop(columns='ID', inplace=True)

    def transform(self):
        """
        transformação dos dados. Engloba várias transformações
        :return: None
        """

        # definição de constantes
        self.interessante = ['regiao', 'estado', 'municipio', 'data', 'dias_caso_0',
                             'obitosAcumulado', 'casosAcumulado', 'obitosNovo', 'casosNovo',
                             'obitosMMhab', 'casosMMhab', 'obitosAcumMMhab', 'casosAcumMMhab']

        self.agrupar_full = ['estado', 'municipio']
        self.agrupar_estado = ['estado']
        self.agrupar_regiao = ['regiao']

        # transformações
        self.substituir_nomes()
        self.consertar_municipios()
        self.dias_desde_caso_0()
        self.casos_obitos_novos()
        self.casos_obitos_ultima_semana()
        self.casos_obitos_percapita()
        self.incidencia()
        self.letalidade()
        self.mortalidade()

        self.suavizacao()
        self.dias_desde_obito_percapita()


        # mais constantes
        self.mask_exc_resumo = ~self.covidbr['municipio'].isin(['Brasil', 'RESUMO'])
        self.mask_exc_resumo_rel = ~self.covidrel['municipio'].isin(['Brasil', 'RESUMO'])

    def substituir_nomes(self):
        """
        substituir nomes relevantes:
            dados em que a contaminação ocorreu fora de um município:
            substituir o nome do município de NaN para 'SEM MUNICÍPIO'

            resumo por estado: substituir o nome do município de NaN para 'RESUMO'

            resumo Brasil: substituir os nomes do munícipio e do estado de NaN para 'Brasil'

        :return: None
        """

        self.mask_forademunicipios = ((self.covidbr['municipio'].isnull()) &
                                 (~self.covidbr['codmun'].isnull()) &
                                 (self.covidbr['codmun'] < 999999) &
                                 (self.covidbr['codmun'] > 99999) &
                                 (self.covidbr['codmun'] % 10**4 == 0))
        mask_resumo_estado = (self.covidbr['municipio'].isnull() & self.covidbr['codmun'].isnull())
        mask_resumo_brasil = (self.covidbr['estado'].isnull())

        self.covidbr.loc[self.covidbr[self.mask_forademunicipios].index, 'municipio'] = 'SEM MUNICÍPIO'
        self.covidbr.loc[self.covidbr[mask_resumo_estado].index, 'municipio'] = 'RESUMO'
        self.covidbr.loc[self.covidbr[mask_resumo_brasil].index, 'municipio'] = 'Brasil'
        self.covidbr.loc[self.covidbr[mask_resumo_brasil].index, 'estado'] = 'Brasil'

    def consertar_municipios(self):
        """
        consertar dados de municipios
            em 21/05/2020, os dados divulgados pelo Ministério da Saúde mudaram. Entre as mudanças,
            os dados pré-20/05 dos municípios passaram a não ser categorizados como tal.
            Essa é uma tentativa de massagear os dados para categorizar corretamente os dados municipais.

            o código de municipio (codmun) é formado por
                EECCCCC
            onde os dois primeiros dígitos são o código do estado e os cinco últimos dígitos correspondem
            ao município. A exceção é EE0000, utilizado para indicar que a doença foi registrada no
            estado, porém sem um município associado.

            Observa-se que, nos casos em que há um estado mas não há codmun, trata-se de uma soma dos
            casos e óbitos de cada estado.

            Os dados divulgados pelo Ministério da Saúde cortam o último dígito do código
            do município nas datas pré-20/05, de forma que a classificação do município fica prejudicada.

            A lógica de classificação dos dados municipais faltantes já foi parcialmente implementada
            na função `substituir_nomes`, especificamente a parte em que o codmun é EE0000. Logo,
            só os nomes de municípios NA é que faltam classificar.

            Assim, a estratégia para consertar os dados municipais será fazer um LEFT JOIN entre o
            dataframe self.covidbr e um dataframe contendo registros com dados municipais. Dessa forma,
            onde não houver dados estes serão preenchidos com o valor do dataframe à direita.
            Ex.: Adamantina, SP, codmun = 3500105. Em algumas linhas registrou-se o codmun de Adamantina
                 como 350010; nestas linhas há dados municipais. No entanto, em outras linhas,
                 registrou-se o codmun de Adamantina como 3500105; nestas linhas não há dados municipais.
                 Após o LEFT JOIN, as linhas em que não há dados municipais (codmun 3500105), os mesmos
                 serão preenchidos.

            Logo, o procedimento deve ser
                1) compilar um dataframe com registros com dados municipais (municipios_conhecidos):
                    linhas em que o município não é NaN mas não está na lista dos municipios
                    extras ('Brasil', 'RESUMO', 'SEM MUNICÍPIO')

                2) no dataframe original, calcular uma coluna codmun_10 = codmun // 10.
                    Nesse caso, aplicar-se-á a todas as linhas, incluindo as que tem registro. No ex
                    acima, a linha em que há registro de Adamantina (codmun 350010), o codmun_10
                    ficaria como 35001. No entanto, nessas linhas o codmun é irrelevante, pois
                    já tem dados municipais.

                3) realizar o LEFT JOIN e limpar as colunas.
                    Após esse passo, teremos, para um mesmo município, dois codmun. No exemplo acima,
                    Adamantina terá codmun 350010 e 3500105.

                4) sanear o dataframe resultante para eliminar essa dupla codificação
                    através de um GroupBy inteligente

                5) sanear o resto do dataframe resultante
                    O saneamento consiste somente de dropar as colunas que foram criadas como
                    resultado intermediário desse processo.

        :return: None
        """

        # passo 1
        municipios_extras = ['Brasil', 'RESUMO', 'SEM MUNICÍPIO']
        mask_municipios_conhecidos = ((~self.covidbr['municipio'].isnull()) &
                                      (~self.covidbr['municipio'].isin(municipios_extras))
                                      )
        municipios_attrs = ['codmun', 'municipio', 'codRegiaoSaude',
                            'nomeRegiaoSaude', 'populacaoTCU2019']
        municipios_conhecidos = self.covidbr[mask_municipios_conhecidos][municipios_attrs]

        # para haver um registro por município
        municipios_conhecidos = municipios_conhecidos.groupby('codmun').first()

        # passo 2
        self.covidbr['codmun_10'] = self.covidbr['codmun']//10

        # passo 3
        self.covidbr = \
            self.covidbr.merge(municipios_conhecidos,
                               left_on='codmun_10', right_on='codmun', how='left')

        for col in municipios_attrs:
            if col == 'codmun':
                continue

            self.covidbr[col] = self.covidbr[col + '_x'].mask(
                cond = self.covidbr[col + '_x'].isnull(),
                other = self.covidbr[col + '_y'])

        # passo 4
        self.covidbr['codmun'] = self.covidbr.groupby(self.agrupar_full)['codmun'].apply(
            lambda x: pd.Series(max(pd.unique(x)), index=x.index))

        # passo 5
        self.covidbr.drop(columns = [ c for c in self.covidbr.columns if '_' in c ], inplace=True)


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

        self.covidbr['obitosAcumMMhab'] = self.covidbr['obitosAcumulado'] / \
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

    def filtro_ultimos_n_dias(self, dias_atras=1, full=False):
        """
        criar um filtro que só mostra os ultimos n dias
        :param dias_atras: n
        :param full: especifica se é o df full (covidbr) ou só os que atingiram 0,1 óbitos / MM hab. (covidrel)
        :return: filtro
        """

        if full:
            c = self.covidbr
        else:
            c = self.covidrel

        return c.data >= dt.datetime.today()-dt.timedelta(days=dias_atras+1)

    def incidencia(self):
        """
        calcula incidencia (total de casos / populacao), por 100 mil hab.
        a incidencia é instável nos primeiros dias da infecção, mas vai ficando mais estável à medida em que a curva de
        infecções vai escapando da exponencial

        :return: None
        """
        self.covidbr['incidencia'] = self.covidbr['casosAcumulado'] / \
        (self.covidbr['populacaoTCU2019'] / (10**5))

    def letalidade(self):
        """
        calcula letalidade (total de obitos / total de casos)

        :return: None
        """
        self.covidbr['letalidade'] = self.covidbr['obitosAcumulado'] / self.covidbr['casosAcumulado']

    def mortalidade(self):
        """
         calcula mortalidade (total de obitos / populacao), por 100 mil hab.

         :return: None
         """
        self.covidbr['mortalidade'] = self.covidbr['obitosAcumulado'] / \
                                     (self.covidbr['populacaoTCU2019'] / (10**5))

    def graf_obitos_acum_por_novos_obitos_loglog_estados(self, data_estados):
        """
        gráfico: óbitos acumulados por MM hab. (log) x novos óbitos na última semana por MM hab (log)
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :return: objetos Axes
        """

        plt.figure()
        ax1o = sns.lineplot(
            data=data_estados, x='obitosAcumMMhab_mm', y='obitos_7d_MMhab_mm', hue='estado',
            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax1o]

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

    def graf_obitos_acum_por_novos_obitos_loglog_municipios(self, data_municipios):
        """
        gráfico: óbitos acumulados por MM hab. (log) x novos óbitos na última semana por MM hab (log)
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municipios
        :return: objetos Axes
        """
        plt.figure()
        ax2o = sns.lineplot(data=data_municipios, x='obitosAcumMMhab_mm', y='obitos_7d_MMhab_mm', hue='municipio',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax2o]

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

    def graf_casos_acum_por_novos_casos_loglog_estados(self, data_estados):
        """
        gráfico: casos acumulados por MM hab. (log) x novos casos na última semana por MM hab (log)
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :return: objetos Axes
        """

        plt.figure()
        ax1c = sns.lineplot(
            data=data_estados, x='casosAcumMMhab_mm', y='casos_7d_MMhab_mm', hue='estado',
            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax1c]

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

    def graf_casos_acum_por_novos_casos_loglog_municipios(self, data_municipios):
        """
        gráfico: casos acumulados por MM hab. (log) x novos casos na última semana por MM hab (log)
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municípios
        :return: objetos Axes
        """

        plt.figure()
        ax2c = sns.lineplot(data=data_municipios, x='casosAcumMMhab_mm', y='casos_7d_MMhab_mm', hue='municipio',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax2c]

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

    def graf_obitos_acum_por_dias_pandemia_log_estados(self, data_estados):
        """
        gráfico: data desde 0.1 óbito por MM hab. x óbitos acumulados por MM hab. (log)
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :return:
        """
        plt.figure()
        ax3o = sns.lineplot(data=data_estados, x='dias_desde_obito_MMhab', y='obitosAcumMMhab_mm', hue='estado',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax3o]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel='Dias desde 0.1 óbito por MM hab.',
                   ylabel='Total de Óbitos (por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
                   title='Evolução da COVID-19 no Brasil (Óbitos)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs

    def graf_obitos_acum_por_dias_pandemia_log_municipios(self, data_municipios):
        """
        gráfico: data desde 0.1 óbito por MM hab. x óbitos acumulados por MM hab. (log)
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municípios
        :return:
        """

        plt.figure()
        ax4o = sns.lineplot(data=data_municipios, x='dias_desde_obito_MMhab', y='obitosAcumMMhab_mm', hue='municipio',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax4o]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel='Dias desde 0.1 óbito por MM hab.',
                   ylabel='Total de Óbitos (por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
                   title='Evolução da COVID-19 no Brasil (Óbitos)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs

    def graf_casos_acum_por_dias_pandemia_log_estados(self, data_estados):
        """
        gráfico: data desde 0.1 óbito por MM hab. x casos acumulados por MM hab. (log)
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :return:
        """

        plt.figure()
        ax3c = sns.lineplot(data=data_estados, x='dias_desde_obito_MMhab', y='casosAcumMMhab_mm', hue='estado',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax3c]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel='Dias desde 0.1 óbito por MM hab.',
                   ylabel='Total de Casos (por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
                   title='Evolução da COVID-19 no Brasil (Infecções)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs

    def graf_casos_acum_por_dias_pandemia_log_municipios(self, data_municipios):
        """
        gráfico: data desde 0.1 óbito por MM hab. x casos acumulados por MM hab. (log)
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municípios
        :return:
        """

        plt.figure()
        ax4c = sns.lineplot(data=data_municipios, x='dias_desde_obito_MMhab', y='casosAcumMMhab_mm', hue='municipio',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax4c]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel='Dias desde 0.1 óbito por MM hab.',
                   ylabel='Total de Casos (por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
                   title='Evolução da COVID-19 no Brasil (Infecções)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs

    def graf_casos_novos_por_dias_pandemia_estados(self, data_estados):
        """
        gráfico: data desde 0.1 óbito por MM hab. x casos novos por MM hab.
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :return:
        """

        plt.figure()
        ax5c = sns.lineplot(data=data_estados, x='dias_desde_obito_MMhab', y='casos_7d_MMhab_mm', hue='estado',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax5c]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel='Dias desde 0.1 óbito por MM hab.',
                   ylabel='Casos Novos (por MM hab., últimos 7 dias, média móvel de ' + str(mm_periodo) + ' dias)',
                   title='Evolução da COVID-19 no Brasil (Infecções)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs

    def graf_casos_novos_por_dias_pandemia_municipios(self, data_municipios):
        """
        gráfico: data desde 0.1 óbito por MM hab. x casos novos por MM hab.
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municípios
        :return:
        """

        plt.figure()
        ax6c = sns.lineplot(data=data_municipios, x='dias_desde_obito_MMhab', y='casos_7d_MMhab_mm', hue='municipio',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax6c]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel='Dias desde 0.1 óbito por MM hab.',
                   ylabel='Casos Novos (por MM hab., últimos 7 dias, média móvel de ' + str(mm_periodo) + ' dias)',
                   title='Evolução da COVID-19 no Brasil (Infecções)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs

    def graficos(self,
                 estados = ('RJ', 'SP', 'AM', 'Brasil'),
                 municipios = ('Niterói', 'Rio de Janeiro', 'São Paulo', 'Brasil')):
        """
        plotar gráficos
        :return: None
        """

        plt_data_estados = self.covidrel[(~self.mask_exc_resumo_rel) & self.covidrel['estado'].isin(estados)]
        plt_data_municipios = self.covidrel[self.covidrel['municipio'].isin(municipios)]

        # executar todas as funções no escopo atual começando por 'graf_'

        func_grafs = [ v for k,v in self.__class__.__dict__.items()
                       if k.startswith('graf_') ]

        self.eixos = []

        for f in func_grafs:
            if f.__name__.endswith('_municipios'):
                arg = plt_data_municipios
            else:
                arg = plt_data_estados

            axs = f(self, arg)
            self.eixos += axs


br = covid_brasil(diretorio = None, graficos = True)

cbr = br.covidrel[~br.mask_exc_resumo_rel].groupby(['regiao', 'estado', 'data']).last()
cbr = cbr.drop(columns=['municipio', 'codmun'])