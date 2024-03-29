#!/usr/env/python3
# -*- coding: utf-8 -*-

#import numpy as np
#import scipy.stats as spst
import numpy as np
import pandas as pd
import os.path
import datetime as dt
import locale
import seaborn as sns
import pickle as pkl
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

    def __init__(self, diretorio=None, graficos=True, dumbcache=False):

        # se diretorio for None, corresponde ao diretorio raiz do script

        if diretorio is None:
            diretorio = r'..'

        # retorna os objetos guardados em um arquivo chamado br_store.dmp na pasta "cache"
        if dumbcache is True:
            self.dumbcache_load()

        else:
            self.covidbr, self.areas, \
            self.areas_estados, self.demobr, \
            self.demomun = self.ler_dados(diretorio)

            self.preproc()
            self.transform()

        if graficos:
            self.graficos()

    def dumbcache_dump(self, cache_dir=r'data\cache'):
        """
        salva os dados para o arquivo br_store.dmp na pasta 'cache'
        dados a serem salvos: self
        :return: None
        """
        obj = self

        DUMBCACHE = os.path.join(r'..', cache_dir, r'br_store.dmp')
        with open(DUMBCACHE, 'wb') as f:
            pkl.dump(obj, f)

    def ler_dados(self, diretorio):
        """
        ler os dados
            1) da planilha excel exposta diariamente por https://covid.saude.gov.br/
            2) de dados geográficos (áreas de municípios e estados) brasileiros

        :param diretorio: o diretório contendo os arquivos excel
        :return: dataframes contendo as informações dos arquivos excel
        """

        # dados da evolução da COVID-19
        # abrir planilha com data de modificação mais recente
        csv_files = [ os.path.join(diretorio, r'data', r'Brasil', f)
                        for f in os.listdir(os.path.join(diretorio, r'data', r'Brasil'))
                        if f.startswith('HIST_PAINEL_COVIDBR') and f.endswith('.csv') ]
        csv_files.sort(key=lambda x:os.path.getmtime(x))
        DATAFILE_DATA_io = csv_files[-1]
        
        cols_dtypes = { k: 'string' for k in [ 'regiao', 'estado', 'municipio', 'nomeRegiaoSaude' ] }
        cols_dtypes.update({
            k: 'Int64' for k in [ 'coduf', 'codmun', 'codRegiaoSaude', 'semanaEpi',
                                  'casosAcumulado', 'casosNovos', 'obitosAcumulado', 'obitosNovos',
                                  'Recuperadosnovos', 'emAcompanhamentoNovos' ]
        })
        
        # mistaken dtypes for correction
        cols_dtypes.update({
            k: 'string' for k in [ 'populacaoTCU2019', 'data' ]
        })
        cols_dtypes_dt = { k: 'datetime64[ns]' for k in ['data'] }
        covid = pd.read_csv(DATAFILE_DATA_io, sep=';',
            encoding='windows-1252', dtype=cols_dtypes
        )

        # dados geográficos dos territórios brasileiros
        DATAFILE_GEO = r'AR_BR_RG_UF_RGINT_RGIM_MES_MIC_MUN_2019.xls'
        DATAFILE_GEO_io = os.path.join(diretorio, r'data', r'Brasil', DATAFILE_GEO)

        areas_mun = pd.read_excel(DATAFILE_GEO_io, sheet_name='AR_BR_MUN_2019')

        areas_estados = pd.read_excel(DATAFILE_GEO_io, sheet_name='AR_BR_UF_2019')

        # dados demográficos agregados do Brasil por sexo
        DATAFILE_DEMOBR = r'br_demografia.csv'
        DATAFILE_DEMOBR_io = os.path.join(diretorio, r'data', r'Brasil', DATAFILE_DEMOBR)

        demo_br = pd.read_csv(DATAFILE_DEMOBR_io, sep=';')

        # dados demográficos agregados do Brasil por município
        DATAFILE_DEMOMUN = r'mun_demografia.csv'
        DATAFILE_DEMOMUN_io = os.path.join(diretorio, r'data', r'Brasil', DATAFILE_DEMOMUN)

        demo_mun = pd.read_csv(DATAFILE_DEMOMUN_io, sep=';')

        return covid, areas_mun, areas_estados, demo_br, demo_mun

    def __preproc_covid(self):
        """
        pre-processamento dos dados brasileiros da doenca
        :return: None
        """

        # processar datas
        
        self.covidbr['data'] = pd.to_datetime(self.covidbr['data'], format='%d/%m/%Y')
        self.covidbr['data'] = self.covidbr['data'].astype(pd.DatetimeTZDtype(tz='America/Sao_Paulo'))

        # 2020-06-02: O Ministério da Saúde cagou os dados de população na planilha divulgada diariamente.
        # devemos consertá-lo
        # regex: ^((?:\d{1,3}\.)*\d*)

        # preencher populacao de areas dos estados que não estão em nenhum município

        pop_estados = self.covidbr[(self.covidbr.estado.notnull()) & (self.covidbr.codmun.isnull())].\
                        groupby('coduf').populacaoTCU2019.first()
        df = self.covidbr.merge(right=pop_estados, on='coduf', how='left')
        populacaoTCU2019 = df.populacaoTCU2019_x.where(df.populacaoTCU2019_x.notnull(), other=df.populacaoTCU2019_y)

        # filtrar dados espúrios de população

        populacaoTCU2019 = populacaoTCU2019.str.extract(r'^((?:\d{1,3}\.)*\d*)', expand=False).\
                           str.replace('.','').astype(float)

        # converter tipos

        df['populacaoTCU2019'] = populacaoTCU2019
        df.drop(columns=[ 'populacaoTCU2019_' + mergedir for mergedir in ['x', 'y'] ], inplace=True)
        self.covidbr = df

        self.covidbr = self.covidbr.astype(
            { converter: 'Int64' for converter in ['coduf', 'codmun', 'codRegiaoSaude', 'populacaoTCU2019',
                      'Recuperadosnovos', 'emAcompanhamentoNovos'] }
        )

    def __preproc_areas(self):
        """
        pre-processamento dos dados geográficos brasileiros
        :return: None
        """
        # deletar nomes que tenham valores NA
        # são valores no excel que estão fora das tabelas e que não tem relevância
        self.areas.dropna(inplace=True)
        self.areas_estados.dropna(inplace=True)

        # renomear colunas
        dict_rename_areas = {
            'CD_GCUF': 'coduf',
            'NM_UF': 'estado_nome',
            'NM_UF_SIGLA': 'estado',
            'CD_GCMUN': 'codmun_10',
            'NM_MUN_2019': 'municipio',
            'AR_MUN_2019': 'area'
        }

        dict_rename_areas_estados = {
            'CD_GCUF': 'coduf',
            'NM_UF': 'estado_nome',
            'NM_UF_SIGLA': 'estado',
            'AR_MUN_2019': 'area'
        }

        self.areas.rename(columns=dict_rename_areas, inplace=True)
        self.areas_estados.rename(columns=dict_rename_areas_estados, inplace=True)

        # dividir codmun_10 por 10 para ficar igual ao resto dos DataFrames
        self.areas['codmun'] = self.areas['codmun_10'] // 10

        # acertar tipos das colunas
        self.areas[['coduf', 'codmun']] = self.areas[['coduf', 'codmun']].astype(float).astype('Int64')
        self.areas_estados.coduf = self.areas_estados.coduf.astype(float).astype('Int64')

        # trocar indice ID por indice (estado, municipio) ou estado
        self.areas.set_index(keys=['coduf', 'codmun'], inplace=True)
        self.areas.drop(columns='ID', inplace=True)
        self.areas_estados.set_index(keys='coduf', inplace=True)
        self.areas_estados.drop(columns='ID', inplace=True)

        # calcular área do brasil
        self.area_brasil = pd.DataFrame(
            [ [self.areas_estados['area'].sum(), 'BR', 'Brasil' ] ],
            index=pd.Index([76], name='coduf'),
            columns=['area', 'estado', 'estado_nome']
        )
        self.areas_estados = pd.concat([self.areas_estados, self.area_brasil])

        # LEFT JOIN: primeiro as dos estados e depois as dos municípios.
        intermediario = self.covidbr.merge(self.areas_estados['area'], on='coduf', how='left')
        intermediario = intermediario.merge(self.areas['area'], on='codmun', how='left',
                                            suffixes=('_est', '_mun'))

        # arrumar as colunas em uma só.
        self.covidbr['area'] = intermediario['area_mun'].where(
            ~intermediario['area_mun'].isnull(),
            other=intermediario['area_est']
        )

    def __preproc_demobr(self):
        """
        pre-processamento dos dados demográficos brasileiros
        :return: None
        """
        # eliminar duas ultimas linhas (total e linha aleatória)
        self.demobr.iloc[-2:] = np.nan
        self.demobr.dropna(inplace=True)

        # renomear colunas
        dict_rename_demobr = {
            'Idade simples': 'idade',
            'Masculino': 'masculino',
            'Feminino': 'feminino',
            'Total': 'total'
        }
        self.demobr.rename(columns = dict_rename_demobr, inplace=True)

        # transformar 'idade' em int
        self.demobr['idade'] = self.demobr['idade'].str.split(' ', n=1, expand=True)
        self.demobr.iloc[-1,0] += '+'
        self.demobr['idade'] = self.demobr['idade'].astype('category')

        # alterar tipos das colunas
        self.demobr[['masculino', 'feminino', 'total']] = self.demobr[['masculino', 'feminino', 'total']].astype(int)

        # alterar indice
        self.demobr.set_index(keys='idade', inplace=True)

    def __preproc_demomun(self):
        """
        pre-processamento dos dados demográficos brasileiros municipais
        :return: None
        """
        # eliminar duas últimas linhas (total e linha aleatória)
        self.demomun.iloc[-2:] = np.nan
        self.demomun.dropna(inplace=True)

        # substituir '-' por 0
        self.demomun.replace('-', 0, inplace=True)

        # renomear colunas
        dict_rename_demomun = dict(zip(
            self.demomun.columns[1:-2],
            self.demomun.columns[1:-2].str.replace('a', '_').str.split(' ', n=3).str[0:-1].str.join('')
        ))

        dict_rename_demomun.update({
            self.demomun.columns[-2]: self.demomun.columns[-2].split(' ')[0] + '+'
        })

        dict_rename_demomun.update({
            'Município': 'codmun_municipio',
            'Total': 'pop_total_2015'
        })
        self.demomun.rename(columns=dict_rename_demomun, inplace=True)

        # separar colunas codmun_10 e municipio
        self.demomun[['codmun', 'municipio']] = self.demomun['codmun_municipio'].str.split(' ', n=1, expand=True)
        self.demomun['codmun'] = self.demomun['codmun'].astype(float).astype('Int64')
        self.demomun.drop(columns='codmun_municipio', inplace=True)

        # acertar tipos das colunas
        self.demomun = self.demomun.astype(
            { converter: 'float' for converter in self.demomun.loc[:, :'codmun'].columns }
        )
        self.demomun = self.demomun.astype(
            { converter: 'Int64' for converter in self.demomun.loc[:, :'codmun'].columns }
        )

        # reordenar colunas
        self.demomun = self.demomun.reindex(
            columns=np.hstack([self.demomun.columns.values[::-1][:2],
                               self.demomun.columns[:-2]])
        )

        # processar colunas: ao inves de um dataframe largo com as faixas etarias como colunas, colocar uma coluna
        # chamada 'faixa_etaria'

        self.demomun = self.demomun.melt(
            id_vars=['codmun', 'municipio', 'pop_total_2015'],
            var_name='faixa_etaria', value_name='populacao'
        )
        self.demomun = self.demomun.groupby(by=['codmun', 'faixa_etaria']).first()

        # calcular % de velho
        velhos = self.demomun.loc[(slice(None), slice('60_69', '80+')), :].groupby(level='codmun')['populacao'].sum()

        pop_total = self.demomun.groupby(level='codmun')['populacao'].sum()

        pct_velhos = velhos / pop_total

        self.demo_velhos = pd.concat([velhos, pop_total, pct_velhos], axis=1)
        self.demo_velhos.columns = ['pop_velhos', 'pop_total_2015', 'pct_velhos']

        # resetar index para facilitar trabalho com a coluna 'codmun'
        self.demo_velhos = self.demo_velhos.reset_index()

        # atualizar % velhos nos estados
        self.demo_velhos['coduf'] = self.demo_velhos['codmun'] // 10 ** 4
        velhos_estados = self.demo_velhos.groupby('coduf')['pop_velhos'].sum() / \
                         self.demo_velhos.groupby('coduf')['pop_total_2015'].sum()
        velhos_estados.name = 'pct_velhos'

        # atualizar % velhos no Brasil
        velhos_br = pd.Series(
             self.demo_velhos['pop_velhos'].sum() / self.demo_velhos['pop_total_2015'].sum(),
             name = 'pct_velhos',
             index = pd.Index([76], name='coduf')
        )

        # juntar estados e Brasil
        velhos_estados = pd.concat([velhos_estados, velhos_br])

        # acertar tipos das colunas de demo_velhos
        self.demo_velhos = self.demo_velhos.astype(
            {l: 'Int64' for l in self.demo_velhos.loc[:,:'pop_total_2015'].columns}
        )

        # fazer LEFT JOIN. Primeiro fazer dos estados e depois dos municípios. Dessa forma todos estarão preenchidos.
        # fazer LEFT JOIN self.covidbr <- velhos_estados através da coluna coduf
        intermediario = self.covidbr.merge(velhos_estados, on='coduf', how='left')

        # fazer LEFT JOIN self.covidbr <- self.demo_velhos através da coluna codmun
        intermediario = intermediario.merge(self.demo_velhos[['codmun','pct_velhos']], on='codmun', how='left',
                                          suffixes=('_uf', '_mun'))

        # arrumar a coluna pct_velhos
        # os dois LEFT JOIN deixaram duas colunas, pct_velhos_uf e e pct_velhos_mun. Onde há pct_velhos_mun, usa-se
        # este. Caso contrário, usa-se o pct_velhos_uf.
        self.covidbr['pct_velhos'] = intermediario['pct_velhos_mun'].where(~intermediario['pct_velhos_mun'].isnull(),
                                                                          other = intermediario['pct_velhos_uf'])

    def preproc(self):
        """
        pre-processamento dos dados
        rodar todas as funções cujo nome começa por '__preproc'
        :return: None
        """

        func_preproc = [ v for k, v in self.__class__.__dict__.items()
                           if k.startswith('_covid_brasil__preproc') ] # mangling

        for f in func_preproc:
            _ = f(self)

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

        # função tornada desnecessária em 25/05
        # self.consertar_municipios()

        self.dias_desde_caso_0()
        self.casos_obitos_novos()
        self.casos_obitos_ultima_semana()

        # normalização
        self.normalizacao()

        # cálculos das estatísticas
        self.incidencia()
        self.letalidade()
        self.mortalidade()

        self.suavizacao()

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

        # renomear municipios e estados
        self.covidbr.loc[self.covidbr[self.mask_forademunicipios].index, 'municipio'] = 'SEM MUNICÍPIO'
        self.covidbr.loc[self.covidbr[mask_resumo_estado].index, 'municipio'] = 'RESUMO'
        self.covidbr.loc[self.covidbr[mask_resumo_brasil].index, 'municipio'] = 'Brasil'
        self.covidbr.loc[self.covidbr[mask_resumo_brasil].index, 'estado'] = 'Brasil'

        # acertando o resumo brasileiro para a função de plotagem
        self.covidbr.loc[self.covidbr[mask_resumo_brasil].index, 'codmun'] = 760001

        # local
        self.covidbr['local'] = self.covidbr['municipio'] + ', ' + \
                                self.covidbr['estado']

        self.covidbr.loc[self.covidbr[mask_resumo_estado].index, 'local'] = \
            self.covidbr['estado']

        self.covidbr.loc[self.covidbr[mask_resumo_brasil].index, 'local'] = 'Brasil'

    def consertar_municipios(self):
        """
        consertar dados de municipios
        EDIT: em 25/05 o Ministério da Saúde consertou os dados. Essa função não é mais necessária.

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
            do município nas datas pós-20/05, de forma que a classificação do município fica prejudicada.

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
                    Adamantina será associadas a dois codmun, 350010 e 3500105.

                4) sanear o dataframe resultante para eliminar essa dupla codificação
                    através de um GroupBy inteligente

                5) sanear o resto do dataframe resultante
                    O saneamento consiste de
                    5a) dropar as colunas que foram criadas como resultado intermediário desse
                        processo.
                    5b) aplicar sort() à coluna `data`

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

        # para haver só um registro por município
        municipios_conhecidos = municipios_conhecidos.groupby('codmun').first()
        # obs.: o index de municipios_conhecidos agora é ['codmun'], diferente de self.covidbr (index genérico)

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
        self.covidbr = self.covidbr.sort_values(by=['codmun', 'data'])

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

        #self.covidbr['obitosNovo'] = self.covidbr.groupby(self.agrupar_full)['obitosAcumulado'].diff().fillna(0)
        #self.covidbr['casosNovo'] = self.covidbr.groupby(self.agrupar_full)['casosAcumulado'].diff().fillna(0)

        self.covidbr['obitosNovo'] = self.covidbr['obitosNovos']
        self.covidbr['casosNovo'] = self.covidbr['casosNovos']

    def casos_obitos_ultima_semana(self):
        """
        casos e óbitos na última semana
        :return: None
        """

        #self.covidbr['obitos_7d'] = self.covidbr.groupby(self.agrupar_full)['obitosNovos'].rolling(7).sum().fillna(0)
        #self.covidbr['casos_7d'] = self.covidbr.groupby(self.agrupar_full)['casosNovos'].rolling(7).sum().fillna(0)

        self.covidbr['obitos_7d'] = self.covidbr.groupby(['estado', 'municipio'])['obitosNovos'].apply(
            lambda x: x.rolling(7).sum()
        )
        self.covidbr['casos_7d'] = self.covidbr.groupby(['estado', 'municipio'])['casosNovos'].apply(
            lambda x: x.rolling(7).sum()
        )

    def __norm_casos_obitos_percapita(self):
        """
        calcula o fator de normalização para considerar casos e óbitos por milhão de habitantes

        :return: None
        """

        self.covidbr['norm_percapita'] = 1 / (self.covidbr['populacaoTCU2019'] / (10**6))

    def __norm_densidade_demografica(self):
        """
        calcula o fator de normalização para a densidade demográfica
            - (# casos ou # obitos) / (populacao / area) = (# casos ou # obitos) * area / populacao
            - essencialmente o fator de normalização per capita * área de cada municipio

        :return: None
        """
        self.covidbr['norm_densidade'] = self.covidbr['area'] / \
                                         (self.covidbr['populacaoTCU2019']/1000)

    def __norm_perfil_demografico(self):
        """
        calcula o fator de normalização para o % de idosos na população de cada município
            - (# casos ou # obitos) / (% idosos)

        :return: None
        """

        self.covidbr['norm_demo'] = 1 / self.covidbr['pct_velhos']

    def __norm_conectividade(self):
        """
        calcula o fator de normalizacao para a medida de conectividade de cada cidade, região, etc

        :return:
        """

        pass

    def normalizacao(self):
        """
        calcular fatores de normalização
            - normalização per capita
            - TODO: normalização por densidade populacional
            - TODO: normalização por % velhos na população
            - TODO: normalização por conectividade

        :return: None
        """
        func_norm = [v for k, v in self.__class__.__dict__.items()
                        if k.startswith('_covid_brasil__norm')]  # mangling

        for f in func_norm:
            _ = f(self)

    def fator_normalizacao(self, dados, normalizacao):
        """
        retorna o fator de normalizacao correspondente à normalizacao desejada
        :param dados: dados que contem os fatores de normalizacao
        :param normalizacao: normalizacao desejada.
            pode ser um vetor contendo quaisquer dos itens ['percapita', 'densidade_demografica', 'perfil_demografico']
        :return: o fator de normalizacao correspondente (para cada linha)
        """
        correspondencia = {
            'percapita': 'norm_percapita',
            'densidade_demografica': 'norm_densidade',
            'perfil_demografico': 'norm_demo'
        }

        f = 1

        if normalizacao is None:
            return f

        fatores_mult_cols = [ v for k, v in correspondencia.items() if k in normalizacao ]
        for c in fatores_mult_cols:
            f *= dados[c]

        return f

    def texto_normalizacao(self, normalizacao, crlf):
        """
        retorna o texto explicativo da normalizacao selecionada
        Por exemplo, se deseja-se normalizacao por densidade demográfica e perfil demográfico,
            texto = '(normalizado por densidade demográfica e perfil demográfico)
        :param normalizacao: a normalizacao desejada
        :return: texto
        """
        if normalizacao is None:
            return None

        subst = {
            'percapita': 'MM hab.',
            'densidade_demografica': 'densidade demográfica (1000 hab/km2)',
            'perfil_demografico': '% idosos na população'
        }

        set_norm_almost_all = set(list(subst.keys())[2:])
        set_norm = set(normalizacao) - {'percapita', 'densidade_demografica'}

        t = crlf + '('

        if 'percapita' in normalizacao:
            t += 'por ' + subst['percapita'] + ', '

        elif 'densidade_demografica' in normalizacao:
            t += 'por ' + subst['densidade_demografica'] + ', '

        # interseção de conjuntos:
        #   se algum elemento da normalizacao corresponder a algum elemento da lista de normalizacoes disponíveis
        #   (exceto 'percapita' e 'densidade_demografica', que já foram considerados), então prossiga.
        if set_norm_almost_all & set_norm != set():

            t += 'normalizado por '

            for c in list(set_norm):
                t += subst[c] + ', '

        t = t[:-2] + ')'
        return t

    def norm_grafico(self, dados, normalizacao,
                     x_orig=None, y_orig=None, titulo_x_orig=None, titulo_y_orig=None,
                     norm_xy='y', crlf='\n', plotly=False):
        """
        retorna alguns parametros necessarios para plotagem dos graficos com dados normalizados

        :param dados: os dados (data_estados ou data_municipios)
        :param normalizacao: o vetor que representa a normalizacao desejada
        :param titulo_x_orig: o título do eixo x original
        :param titulo_y_orig: o título do eixo y original
        :param norm_xy: os eixos em que se deseja aplicar a normalizacao. Pode ser 'x', 'y' ou 'xy'
        :return: vetor com
            dados_normalizados: dataframe (cópia) contendo valores originais e valores normalizados
            titulo_x, titulo_y: os valores dos titulos dos eixos após explicação da normalizacao
        """
        dados = dados.copy()

        # calcular o fator de normalizacao
        f = self.fator_normalizacao(dados=dados, normalizacao=normalizacao)
        f_titulo = self.texto_normalizacao(normalizacao=normalizacao, crlf=crlf)
        if f_titulo is None:
            f_titulo = ''

        # aplicar o fator de normalizacao a cada eixo, caso apropriado
        if not plotly:
            dados['x'] = dados[x_orig]
            titulo_x = titulo_x_orig
            if 'x' in norm_xy:
                dados['x'] *= f
                titulo_x += f_titulo

            dados['y'] = dados[y_orig]
            titulo_y = titulo_y_orig
            if 'y' in norm_xy:
                dados['y'] *= f
                titulo_y += f_titulo

            return dados, titulo_x, titulo_y
        else:
            titulo_orig = dict()

            tipo_graf_all = [
                ['obitos', 'casos'],
                ['total', 'novos'],
                ['temporal', 'atemporal']
            ]
            
            texto_mm = { mm: 'média móvel de ' + str(mm) + ' dias' for mm in [0, 3, 5, 7] }
            texto_mm[0] = ''

            for axis in ['x', 'y']:
                combinations = list(pd.MultiIndex.from_product(tipo_graf_all))
                if axis == 'x':
                    key = { k: v for k, v in zip(
                        combinations,
                        [
                            'dias_desde_obito_MMhab', 'obitosAcumulado', 'dias_desde_obito_MMhab', 'obitosAcumulado',
                            'dias_desde_obito_MMhab', 'casosAcumulado', 'dias_desde_obito_MMhab', 'casosAcumulado'
                        ]
                    ) }
                else:
                    key = { k: v for k, v in zip(
                        combinations,
                        [
                            'obitosAcumulado', 'obitos_7d', 'obitos_7d', 'obitos_7d',
                            'casosAcumulado', 'casos_7d', 'casos_7d', 'casos_7d'
                        ]
                    ) }

                for comb in combinations:
                    for mm in texto_mm.keys():
                        mm_str = str(mm)
                        str_key = axis + '_'
                        for c in comb:
                            str_key += c[0]
                            
                        str_key += mm_str
    
                        # se o eixo x for temporal, não faz sentido fazer média movel
                        if str_key[:-1].endswith('t') and str_key.startswith('x'):
                            dados[str_key] = dados[key[comb]]
                        else:
                            dados[str_key] = dados[key[comb] + '_mm' + mm_str]
    
                        # titulos do eixo x
                        if axis == 'x':

                            # se eixo x for temporal, só existe uma possibilidade: dias desde o começo da pandemia
                            if str_key[:-1].endswith('t'):
                                titulo_orig[str_key] = 'Dias desde 0.1 óbitos / MM hab.'
    
                            # se eixo x for atemporal, há duas possibilidades: total de óbitos ou total de casos
                            elif 'o' in str_key:
                                titulo_orig[str_key] = 'Total de óbitos'
                                if texto_mm[mm] != '':
                                    titulo_orig[str_key] = titulo_orig[str_key] + ' (' + texto_mm[mm] + ')'
    
                            # caso eixo x seja atemporal mas não seja óbitos, então é total de casos
                            else:
                                titulo_orig[str_key] = 'Total de casos'
                                if texto_mm[mm] != '':
                                    titulo_orig[str_key] = titulo_orig[str_key] + ' (' + texto_mm[mm] + ')'
    
                        else:
                            # há seis possibilidades para o eixo y.
                            # se gráfico for atemporal, só há duas possibilidades, novos casos ou novos óbitos
                            if 'a' in str_key:
                                if 'o' in str_key:
                                    titulo_orig[str_key] = 'Novos óbitos (últ. 7 dias)'
                                    if texto_mm[mm] != '':
                                        titulo_orig[str_key] = titulo_orig[str_key][:-1] + ', ' + texto_mm[mm] + ')'
                                else:
                                    titulo_orig[str_key] = 'Novos casos (últ. 7 dias)'
                                    if texto_mm[mm] != '':
                                        titulo_orig[str_key] = titulo_orig[str_key][:-1] + ', ' + texto_mm[mm] + ')'
    
                            # se o gráfico for temporal, então há quatro possibilidades para o eixo y
                            else:
                                # novos óbitos
                                if 'o' in str_key:
                                    if 'n' in str_key:
                                        titulo_orig[str_key] = 'Novos óbitos (últ. 7 dias)'
                                        if texto_mm[mm] != '':
                                            titulo_orig[str_key] = titulo_orig[str_key][:-1] + ', ' + texto_mm[mm] + ')'
                                            
                                    # total de óbitos
                                    else:
                                        titulo_orig[str_key] = 'Total de Óbitos'
                                        if texto_mm[mm] != '':
                                            titulo_orig[str_key] = titulo_orig[str_key] + ' (' + texto_mm[mm] + ')'
    
                                else:
                                    # novos casos
                                    if 'n' in str_key:
                                        titulo_orig[str_key] = 'Novos casos (últ. 7 dias)'
                                        if texto_mm[mm] != '':
                                            titulo_orig[str_key] = titulo_orig[str_key][:-1] + ', ' + texto_mm[mm] + ')'
    
                                    # total de casos
                                    else:
                                        titulo_orig[str_key] = 'Total de casos'
                                        if texto_mm[mm] != '':
                                            titulo_orig[str_key] = titulo_orig[str_key] + ' (' + texto_mm[mm] + ')'

            titulo = titulo_orig.copy()
            for k, v in titulo.items():
                if k[0] in norm_xy:
                    dados[k] *= f
                    titulo[k] += f_titulo

            return dados, titulo, titulo

    def suavizacao(self):
        """
        suavização via média móvel com período definido anteriormente
        :return: None
        """

        mm_aplicar = ['obitosAcumulado', 'obitos_7d',
                        'casosAcumulado', 'casos_7d',
                        'casosNovo', 'obitosNovo'
                      ]
        for janela_mm in [ 0, 3, 5, 7]:
            
            mm_aplicado = [mm + '_mm' + str(janela_mm) for mm in mm_aplicar]
            
            if janela_mm != 0:
                
                df = self.covidbr.groupby(self.agrupar_full)[mm_aplicar].\
                    rolling(janela_mm).mean()
                df = df.set_index(df.index.get_level_values(None))
                df.columns = mm_aplicado
                
                self.covidbr = pd.concat([self.covidbr, df], axis=1)
                
            else:
                self.covidbr[mm_aplicado] = self.covidbr[mm_aplicar]

        self.dias_desde_obito_percapita()

    def dias_desde_obito_percapita(self):
        """
        cálculo de # de dias desde 0.1 obito por MM hab
        :return: None
        """
        self.mask_obitoMMhab = self.covidbr['obitosAcumulado'] * self.covidbr['norm_percapita'] >= 0.1

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

    def __graf_obitos_acum_por_novos_obitos_loglog_estados(self, data_estados, normalizacao):
        """
        gráfico: óbitos acumulados por MM hab. (log) x novos óbitos na última semana por MM hab (log)
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :return: objetos Axes
        """

        dados_normalizados, titulo_x, titulo_y = self.norm_grafico(
            dados=data_estados,
            normalizacao=normalizacao,
            x_orig='obitosAcumulado_mm',
            y_orig='obitos_7d_mm',
            titulo_x_orig='Total de Óbitos (média móvel de ' + str(mm_periodo) + ' dias)',
            titulo_y_orig='Novos Óbitos (últ. 7 dias, média móvel de ' + str(mm_periodo) + ' dias)',
            norm_xy='xy'
        )

        plt.figure()
        ax = sns.lineplot(data=dados_normalizados, x='x', y='y', hue='estado',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax]

        for ax in axs:
            ax.set(xscale='log', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel=titulo_x,
                   ylabel=titulo_y,
                   title='Evolução da COVID-19 no Brasil (Óbitos)')

            ax.get_yaxis().set_major_formatter(CustomTicker())
            ax.get_xaxis().set_major_formatter(CustomTicker())

        return axs

    def __graf_obitos_acum_por_novos_obitos_loglog_municipios(self, data_municipios, normalizacao):
        """
        gráfico: óbitos acumulados por MM hab. (log) x novos óbitos na última semana por MM hab (log)
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municipios
        :return: objetos Axes
        """
        dados_normalizados, titulo_x, titulo_y = self.norm_grafico(
            dados=data_municipios,
            normalizacao=normalizacao,
            x_orig='obitosAcumulado_mm',
            y_orig='obitos_7d_mm',
            titulo_x_orig='Total de Óbitos (média móvel de ' + str(mm_periodo) + ' dias)',
            titulo_y_orig='Novos Óbitos (últ. 7 dias, média móvel de ' + str(mm_periodo) + ' dias)',
            norm_xy='xy'
        )

        plt.figure()
        ax = sns.lineplot(data=dados_normalizados, x='x', y='y', hue='municipio',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax]

        for ax in axs:
            ax.set(xscale='log', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel=titulo_x,
                   ylabel=titulo_y,
                   title='Evolução da COVID-19 no Brasil (Óbitos)')

            ax.get_yaxis().set_major_formatter(CustomTicker())
            ax.get_xaxis().set_major_formatter(CustomTicker())

        return axs

    def __graf_casos_acum_por_novos_casos_loglog_estados(self, data_estados, normalizacao):
        """
        gráfico: casos acumulados por MM hab. (log) x novos casos na última semana por MM hab (log)
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :return: objetos Axes
        """

        dados_normalizados, titulo_x, titulo_y = self.norm_grafico(
            dados=data_estados,
            normalizacao=normalizacao,
            x_orig='casosAcumulado_mm',
            y_orig='casos_7d_mm',
            titulo_x_orig='Total de Casos (média móvel de ' + str(mm_periodo) + ' dias)',
            titulo_y_orig='Novos Casos (últ. 7 dias, média móvel de ' + str(mm_periodo) + ' dias)',
            norm_xy='xy'
        )

        plt.figure()
        ax = sns.lineplot(data=dados_normalizados, x='x', y='y', hue='estado',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax]

        for ax in axs:
            ax.set(xscale='log', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel=titulo_x,
                   ylabel=titulo_y,
                   title='Evolução da COVID-19 no Brasil (Infecções)')

            ax.get_yaxis().set_major_formatter(CustomTicker())
            ax.get_xaxis().set_major_formatter(CustomTicker())

        return axs

    def __graf_casos_acum_por_novos_casos_loglog_municipios(self, data_municipios, normalizacao):
        """
        gráfico: casos acumulados por MM hab. (log) x novos casos na última semana por MM hab (log)
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municípios
        :return: objetos Axes
        """

        dados_normalizados, titulo_x, titulo_y = self.norm_grafico(
            dados=data_municipios,
            normalizacao=normalizacao,
            x_orig='casosAcumulado_mm',
            y_orig='casos_7d_mm',
            titulo_x_orig='Total de Casos (média móvel de ' + str(mm_periodo) + ' dias)',
            titulo_y_orig='Novos Casos (últ. 7 dias, média móvel de ' + str(mm_periodo) + ' dias)',
            norm_xy='xy'
        )

        plt.figure()
        ax = sns.lineplot(data=dados_normalizados, x='x', y='y', hue='municipio',
                            err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax]

        for ax in axs:
            ax.set(xscale='log', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel=titulo_x,
                   ylabel=titulo_y,
                   title='Evolução da COVID-19 no Brasil (Infecções)')

            ax.get_yaxis().set_major_formatter(CustomTicker())
            ax.get_xaxis().set_major_formatter(CustomTicker())

        return axs

    def __graf_obitos_acum_por_dias_pandemia_log_estados(self, data_estados, normalizacao):
        """
        gráfico: data desde 0.1 óbito por MM hab. x óbitos acumulados por MM hab. (log)
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :return:
        """
        dados_normalizados, titulo_x, titulo_y = self.norm_grafico(
            dados=data_estados,
            normalizacao=normalizacao,
            x_orig='dias_desde_obito_MMhab',
            y_orig='obitosAcumulado_mm',
            titulo_x_orig='Dias desde 0.1 óbito por MM hab.',
            titulo_y_orig='Total de Óbitos (média móvel de ' + str(mm_periodo) + ' dias)',
            norm_xy='y'
        )

        plt.figure()
        ax = sns.lineplot(data=dados_normalizados, x='x', y='y', hue='estado',
                          err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel=titulo_x,
                   ylabel=titulo_y,
                   title='Evolução da COVID-19 no Brasil (Óbitos)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs

    def __graf_obitos_acum_por_dias_pandemia_log_municipios(self, data_municipios, normalizacao):
        """
        gráfico: data desde 0.1 óbito por MM hab. x óbitos acumulados por MM hab. (log)
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municípios
        :return:
        """

        dados_normalizados, titulo_x, titulo_y = self.norm_grafico(
            dados=data_municipios,
            normalizacao=normalizacao,
            x_orig='dias_desde_obito_MMhab',
            y_orig='obitosAcumulado_mm',
            titulo_x_orig='Dias desde 0.1 óbito por MM hab.',
            titulo_y_orig='Total de Óbitos (média móvel de ' + str(mm_periodo) + ' dias)',
            norm_xy='y'
        )

        plt.figure()
        ax = sns.lineplot(data=dados_normalizados, x='x', y='y', hue='municipio',
                          err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel=titulo_x,
                   ylabel=titulo_y,
                   title='Evolução da COVID-19 no Brasil (Óbitos)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs

    def __graf_casos_acum_por_dias_pandemia_log_estados(self, data_estados, normalizacao):
        """
        gráfico: data desde 0.1 óbito por MM hab. x casos acumulados por MM hab. (log)
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :return:
        """

        dados_normalizados, titulo_x, titulo_y = self.norm_grafico(
            dados=data_estados,
            normalizacao=normalizacao,
            x_orig='dias_desde_obito_MMhab',
            y_orig='casosAcumulado_mm',
            titulo_x_orig='Dias desde 0.1 óbito por MM hab.',
            titulo_y_orig='Total de Casos (média móvel de ' + str(mm_periodo) + ' dias)',
            norm_xy='y'
        )

        plt.figure()
        ax = sns.lineplot(data=dados_normalizados, x='x', y='y', hue='estado',
                          err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel=titulo_x,
                   ylabel=titulo_y,
                   title='Evolução da COVID-19 no Brasil (Infecções)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs

    def __graf_casos_acum_por_dias_pandemia_log_municipios(self, data_municipios, normalizacao):
        """
        gráfico: data desde 0.1 óbito por MM hab. x casos acumulados por MM hab. (log)
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municípios
        :return:
        """

        dados_normalizados, titulo_x, titulo_y = self.norm_grafico(
            dados=data_municipios,
            normalizacao=normalizacao,
            x_orig='dias_desde_obito_MMhab',
            y_orig='casosAcumulado_mm',
            titulo_x_orig='Dias desde 0.1 óbito por MM hab.',
            titulo_y_orig='Total de Casos (média móvel de ' + str(mm_periodo) + ' dias)',
            norm_xy='y'
        )

        plt.figure()
        ax = sns.lineplot(data=dados_normalizados, x='x', y='y', hue='municipio',
                          err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel='Dias desde 0.1 óbito por MM hab.',
                   ylabel='Total de Casos (por MM hab., média móvel de ' + str(mm_periodo) + ' dias)',
                   title='Evolução da COVID-19 no Brasil (Infecções)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs

    def __graf_casos_novos_por_dias_pandemia_estados(self, data_estados, normalizacao):
        """
        gráfico: data desde 0.1 óbito por MM hab. x casos novos por MM hab.
        :param data_estados: dados usados pelo seaborn para plotar o gráfico dos estados
        :return:
        """

        dados_normalizados, titulo_x, titulo_y = self.norm_grafico(
            dados=data_estados,
            normalizacao=normalizacao,
            x_orig='dias_desde_obito_MMhab',
            y_orig='casosNovo_mm',
            titulo_x_orig='Dias desde 0.1 óbito por MM hab.',
            titulo_y_orig='Casos Novos (últ. 7 dias, média móvel de ' + str(mm_periodo) + ' dias)',
            norm_xy='y'
        )

        plt.figure()
        ax = sns.lineplot(data=dados_normalizados, x='x', y='y', hue='estado',
                          err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel=titulo_x,
                   ylabel=titulo_y,
                   title='Evolução da COVID-19 no Brasil (Infecções)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs

    def __graf_casos_novos_por_dias_pandemia_municipios(self, data_municipios, normalizacao):
        """
        gráfico: data desde 0.1 óbito por MM hab. x casos novos por MM hab.
        :param data_municipios: dados usados pelo seaborn para plotar o gráfico dos municípios
        :return:
        """

        dados_normalizados, titulo_x, titulo_y = self.norm_grafico(
            dados=data_municipios,
            normalizacao=normalizacao,
            x_orig='dias_desde_obito_MMhab',
            y_orig='casosNovo_mm',
            titulo_x_orig='Dias desde 0.1 óbito por MM hab.',
            titulo_y_orig='Casos Novos (últ. 7 dias, média móvel de ' + str(mm_periodo) + ' dias)',
            norm_xy='y'
        )

        plt.figure()
        ax = sns.lineplot(data=dados_normalizados, x='x', y='y', hue='municipio',
                          err_style=None)
        plt.tight_layout()
        sns.despine()

        axs = [ax]

        for ax in axs:
            ax.set(xscale='linear', yscale='log',
                   xticks={'minor': True}, yticks={'minor': True},
                   adjustable='datalim',
                   xlabel=titulo_x,
                   ylabel=titulo_y,
                   title='Evolução da COVID-19 no Brasil (Infecções)')
            ax.get_yaxis().set_major_formatter(CustomTicker())

        return axs

    def graficos(self,
                 estados = ('RJ', 'SP', 'AM', 'Brasil'),
                 municipios = ('Niterói', 'Rio de Janeiro', 'São Paulo', 'Brasil'),
                 normalizacao = ('percapita',)):
        """
        plotar gráficos
        :return: None
        """

        plt_data_estados = self.covidrel[(~self.mask_exc_resumo_rel) & self.covidrel['estado'].isin(estados)]
        plt_data_municipios = self.covidrel[self.covidrel['municipio'].isin(municipios)]

        # executar todas as funções no escopo atual começando por '__graf'

        func_grafs = [ v for k,v in self.__class__.__dict__.items()
                       if k.startswith('_covid_brasil__graf') ] # mangling

        self.eixos = []

        for f in func_grafs:
            if f.__name__.endswith('_municipios'):
                arg = plt_data_municipios
            else:
                arg = plt_data_estados

            axs = f(self, arg, normalizacao)
            self.eixos += axs


def dumbcache_load(cache_dir=r'data\cache'):
    """
    carrega os dados salvos via pickle na pasta cache, no arquivo br_store.dmp
    :return: instancia da classe covid_brasil
    """
    DUMBCACHE = os.path.join(r'..', cache_dir, r'br_store.dmp')
    with open(DUMBCACHE, 'rb') as f:
        return pkl.load(f)

if __name__ == '__main__':
    br = covid_brasil(diretorio = None, graficos = False)

    cbr = br.covidrel[~br.mask_exc_resumo_rel].groupby(['regiao', 'estado', 'data']).last()
    cbr = cbr.drop(columns=['municipio', 'codmun'])