#!/usr/env/python3
# -*- coding: utf-8 -*-

#import numpy as np
#import scipy.stats as spst
import pandas as pd
import os
import os.path
import datetime as dt
import functools as ft
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

class covid_plot:
    """ classe para plotagem da evolução da COVID-19 no Brasil e no mundo """

    def __init__(self, br, world=None):
        self.br = br # classe covid_brasil
        self.world = world # classe para representar o mundo (ainda não implementada)

        br = covid.covid_brasil(diretorio=None, graficos=False)

        data_estados = ['Brasil', 'RJ']
        data_municipios = ['Brasil', 'Niterói', 'Rio de Janeiro']
        normalizacao = ['percapita']

        self.fig, self.df_norm, self.titulo = self.construir_figura(data_estados, data_municipios, normalizacao)
        self.atualizar_figura()
        self.updatemenu(data_estados, data_municipios)
        self.salvar(html_fig = r'..\imgs (nogit)\img.html')

        self.dash_builder = {}
        self.dashapp = self.dash_build()

    def construir_figura(self, data_estados, data_municipios, normalizacao):
        """
        construir o plot do plotly
        :return: dicionario Figure do Plotly
        """

        br = self.br
        df = br.covidrel[(~br.mask_exc_resumo_rel) & (br.covidrel['estado'].isin(data_estados))]
        df_est = br.covidrel[br.mask_exc_resumo_rel]
        self.estados_key = df_est.groupby('coduf')['estado'].first()

        df_mun = br.covidrel[br.mask_exc_resumo_rel]
        self.municipios_key = df_mun.groupby('codmun')[['estado', 'municipio']].first()

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

        fig1 = px.line(df_norm, x='x_ott', y='y_ott', color='estado', log_y=True, hover_name='estado')

        fig = fig1

        return fig, df_norm, titulo

    def atualizar_figura(self):
        """
        atualizar a figura com
        :return:
        """
        self.fig.update_traces(connectgaps=True,
                          hovertemplate=
                          '<b>%{y:.1f} casos novos</b> / MM hab. nos 7 dias anteriores'
                          )

        self.fig.update_layout(hovermode='x unified',
                          title_text='Evolução da COVID-19 no Brasil (Óbitos)')

        self.fig.update_yaxes(title_text=self.titulo['y_ont'])
        self.fig.update_xaxes(title_text=self.titulo['x_ont'])

    def updatemenu(self, data_estados, data_municipios):
        """
        construir updatemenu
        :return: None
        """
        df_norm = self.df_norm

        log_linear = [{
            'active': 0,
            'y': 1, 'x': 0,
            'xanchor': 'left', 'yanchor': 'top',
            'type': 'dropdown',
            'buttons': [
                {'label': 'Log',
                 'method': 'relayout',
                 'args': ['yaxis', {'type': 'log',
                                    'title': {'text': self.titulo['y_ont']}}]
                 },
                {'label': 'Linear',
                 'method': 'relayout',
                 'args': ['yaxis', {'type': 'linear',
                                    'title': {'text': self.titulo['y_ont']}}]
                 }
            ]
        }, {
            'active': 1,
            'y': 0, 'x': 1,
            'xanchor': 'right', 'yanchor': 'bottom',
            'type': 'dropdown', 'direction': 'left',
            'buttons': [
                {'label': 'Log',
                 'method': 'relayout',
                 'args': ['xaxis', {'type': 'log',
                                    'title': {'text': self.titulo['x_ont']}}]
                 },
                {'label': 'Linear',
                 'method': 'relayout',
                 'args': ['xaxis', {'type': 'linear',
                                    'title': {'text': self.titulo['x_ont']}}]
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
                args=[{'x': [df_norm[df_norm['estado'] == c].x_ott for c in data_estados],
                       'y': [df_norm[df_norm['estado'] == c].y_ott for c in data_estados]
                       }]
            ), dict(
                label='casos',
                method='restyle',
                args=[{'x': [df_norm[df_norm['estado'] == c].x_ctt for c in data_estados],
                       'y': [df_norm[df_norm['estado'] == c].y_ctt for c in data_estados],
                       'xaxis': {'title': {'text': self.titulo['x_cnt']}},
                       'yaxis': {'title': {'text': self.titulo['y_cnt']}},
                       }]
            )
            ]
        )]

        annot_obitos_casos = [
            dict(text="Tipo", showarrow=False,
                 x=0.5, y=1.09, yref="paper", xref='paper',
                 xanchor='right', yanchor='bottom',
                 font_size=16
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
                 font_size=16
                 )
        ]

        self.fig.update_layout(updatemenus=log_linear  # + obitos_casos + total_novos,
                          # annotations=annot_obitos_casos + annot_total_novos)
                          )

    def __dash_cabecalho(self):
        """

        :return: None
        """
        self.dash_builder['cabecalho'] =\
            [ html.H1(children='Evolução da COVID-19 no Brasil'),
                      html.Div(children='''
                      Uma análise de dados da COVID-19 do Brasil e do mundo.
                      \n\n\n        
                      ''')
            ]

    def __dash_grafico(self):
        """

        :return: None
        """
        self.dash_builder['grafico'] = [
            dcc.Graph(id='covid',
                      figure=self.fig
                      )
        ]

    def __dash_opcoes(self):
        """

        :return: None
        """
        opcao_municipio = [
            html.Label('Municípios', className='opcoes-label'),
            dcc.Dropdown(
                id='opcao_municipio',
                options=[
                    {'label': self.municipios_key.loc[codmun, 'municipio'] + ', ' + \
                              self.municipios_key.loc[codmun, 'estado'],
                     'value': codmun}
                    for codmun in self.municipios_key.index
                ],
                value=[330330, 330445],
                multi=True
            )
        ]

        opcao_estado = [
            html.Label('Estados', className='opcoes-label'),
            dcc.Dropdown(
                id='opcao_estado',
                options=[
                    {'label': self.estados_key[coduf], 'value': coduf} for coduf in self.estados_key.index
                ],
                value=[33, 34, 76],
                multi=True
            ),
        ]

        opcao_suavizacao = [
            html.Label('Suavização', className='opcoes-label'),
            dcc.RadioItems(
                id='opcao_suavizacao',
                options=[
                    {'label': 'Sem suavização', 'value': 0},
                    {'label': 'Média móvel de 7 dias', 'value': 7},
                    {'label': 'Média móvel de 3 dias', 'value': 3},
                    {'label': 'Outra média móvel', 'value': -1}
                ],
                value=7
            ),
            dcc.Input(
                id='opcao_suavizacao_custom',
                value=5, type='number'
            )
        ]

        opcoes_lista = [opcao_municipio + opcao_estado, opcao_suavizacao]

        opcoes_lista_div = [
            html.Div(children=opcao, className='opcoes')
            for opcao in opcoes_lista
        ]

        self.dash_builder['opcoes_grid'] = [
            html.Div(children=opcoes_lista_div,
                     style={'display': 'grid',
                            'grid-template-columns': 'repeat(3, 1fr)',
                            'grid-gap': '30px'
                            })
        ]

    def dash_build(self):
        """
        construção do aplicativo Dash
        rodar todas as funções cujo nome começa por '__dash'
        :return: app
        """

        func_dash_build = [ v for k, v in self.__class__.__dict__.items()
                           if k.startswith('_covid_plot__dash') ] # mangling

        for f in func_dash_build:
            _ = f(self)

        external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
        app = dash.Dash('COVID-19: Dados, evolução e prognóstico', external_stylesheets=external_stylesheets)

        app.layout = html.Div(children=ft.reduce(lambda x,y:x+y, self.dash_builder.values()))

        return app

    def salvar(self, html_fig=None, img=None):
        """
        salvar as figuras
        :return: None
        """
        if html_fig is not None:
            self.fig.write_html(html_fig)

        if img is not None:
            self.fig.write_image(img)


br = covid.covid_brasil(diretorio = None, graficos = False)

plt = covid_plot(br)

if __name__ == '__main__':
    if os.environ['PYCHARM_HOSTED'] == 0:
        plt.dashapp.run_server(debug=True)