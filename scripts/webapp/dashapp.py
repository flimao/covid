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

import plotly.graph_objs as go
import plotly.express as px
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State

from thesmuggler import smuggle

covid = smuggle(r'..\covid.py')
covid_brasil = covid.covid_brasil

##
# parâmetros
# ##
mm_periodo = 5

class covid_plot:
    """ classe para plotagem da evolução da COVID-19 no Brasil e no mundo """

    def __init__(self, br, world=None):
        self.br = br # classe covid_brasil
        self.world = world # classe para representar o mundo (ainda não implementada)

        self.estados_key, self.municipios_key = self.construir_indice()

        # Brasil e RJ
        data_estados = [76, 33]

        # Brasil e Niterói, RJ
        data_municipios = [ 760001, 330330 ]
        normalizacao = ['percapita']

        x, y = self.selec_xy(obitos_casos = 'obitos',
                             total_novos = 'total',
                             tempo_atempo = 'tempo')

        self.fig, self.df_norm, self.titulo = self.construir_figura(
            data_estados, data_municipios, normalizacao, x, y
        )
        self.atualizar_figura(x, y)
        self.salvar(html_fig = r'..\imgs (nogit)\img.html')

        self.dash_builder = {}
        self.dashapp = self.dash_build(debug=True)

        # callbacks
        self.dashapp.callback(
            Output(component_id='covid', component_property='figure'),
            [   Input(component_id='xlog', component_property='value'),
                Input(component_id='ylog', component_property='value'),
                Input(component_id='opcao_estado', component_property='value'),
                Input(component_id='opcao_municipio', component_property='value'),
                Input(component_id='opcao_obitos_casos', component_property='value'),
                Input(component_id='opcao_total_novos', component_property='value'),
                Input(component_id='opcao_eixox_tempo', component_property='value'),
                Input(component_id='opcao_suavizacao', component_property='value'),
                Input(component_id='opcao_norm_pop', component_property='value'),
                Input(component_id='opcao_norm_extra', component_property='value'),
                Input(component_id='opcao_norm_xy', component_property='value')
            ],[
                State(component_id='covid', component_property='figure')
            ]
        )(self.atualizar_grafico)
        self.dashapp.callback(
            [Output(component_id='xlog', component_property='value'),
             Output(component_id='opcao_norm_xy', component_property='value')],
            [Input(component_id='opcao_eixox_tempo', component_property='value'),
             Input(component_id='ylog', component_property='value')],
            [State(component_id='opcao_norm_xy', component_property='value')]
        )(self.escala_eixo)

    def construir_indice(self):
        """
        Construir índice de estados e municípios
        :return: índice de estados e munícipios
        """
        # construindo referencia de coduf e codmun
        df_exc = br.covidrel[br.mask_exc_resumo_rel]
        estados_key = df_exc.groupby('coduf')['estado'].first()
        municipios_key = df_exc.groupby('codmun')['local'].first()

        # comparando com Brasil
        est_br = pd.Series(['Brasil'], index=pd.Index([76], name='coduf'), name='estado')
        # já existe um codmun para o Brasil, 760001

        #mun_br = pd.DataFrame([['Brasil'],],
        #                      columns=['local'],
        #                      index=pd.Index([76001], name='codmun')
        #                      )

        estados_key = pd.concat([estados_key, est_br])
        #municipios_key = pd.concat([municipios_key, mun_br])

        return estados_key, municipios_key

    def construir_figura(self, data_estados, data_municipios, normalizacao,
                         x='x_ott', y='y_ott',
                         suavizacao=7, norm_xy='y'):
        """
        construir o plot do plotly
        :return: dicionario Figure do Plotly
        """
        
        br = self.br
        crel = br.covidrel.copy()
        df_est = crel[(~br.mask_exc_resumo_rel) & (crel['coduf'].isin(data_estados))]
        df_mun = crel[(br.mask_exc_resumo_rel) & (crel['codmun'].isin(data_municipios))]
        df = pd.concat([df_est, df_mun])

        df_norm, titulo, _ = br.norm_grafico(
            dados=df,
            normalizacao=normalizacao,
            norm_xy=norm_xy, crlf='<br>', plotly=True
        )
        
        x_s = x + str(suavizacao)
        y_s = y + str(suavizacao)
        
        fig1 = px.line(df_norm, x=x_s, y=y_s, color='local', log_y=True, hover_name='local')

        fig = fig1

        return fig, df_norm, titulo

    def atualizar_figura(self, x, y, xlog='linear', ylog='log', suavizacao=7,
                         obitos_casos='obitos', tempo_atempo = 'tempo',
                         normalizacao_pop='densidade_demografica',
                         data_estados=[33], data_municipios=[330330]):
        """
        atualizar a figura com
        :return:
        """

        dict_trad = {
            'obitos': 'óbitos',
            'casos': 'casos'
        }
        self.fig.update_traces(connectgaps=True)

        self.fig.update_layout(xaxis_type=xlog, yaxis_type=ylog)
        
        x_s = x + str(suavizacao)
        y_s = y + str(suavizacao)

        if normalizacao_pop == 'densidade_demografica':
            for i, data in enumerate(self.fig['data']):
                local = data['name']
                if self.estados_key[data_estados].isin([local]).any():
                    self.fig['data'][i]['visible'] = 'legendonly'
        #else:
        #    for i in range(len(self.fig['data'])):
        #        self.fig['data'][i]['visible'] = True
        
        # se o eixo x for tempo, o título é o do gráfico
        if tempo_atempo == 'tempo':
            self.fig.update_layout(
                hovermode = 'x unified',
                title_text = self.titulo[y_s],
                yaxis_title_text = '',
                xaxis_title_text = self.titulo[x_s]
            )
            self.fig.update_traces(
                hovertemplate='%{y:.1f} ' + dict_trad[obitos_casos]
            )
        # caso contrário, o título vai para o eixo y, e o hovermode muda
        else:
            self.fig.update_layout(
                hovermode = 'x',
                title_text = 'Evolução da COVID-19 (' + dict_trad[obitos_casos] + ')',
                yaxis_title_text = self.titulo[y_s],
                xaxis_title_text = self.titulo[x_s]
            )
            self.fig.update_traces(
                hovertemplate='%{y:.1f} ' + dict_trad[obitos_casos]
            )

    def __dash_cabecalho(self):
        """

        :return: None
        """
        self.dash_builder['cabecalho'] =[
            html.H1(children='Evolução da COVID-19 no Brasil'),
            dcc.Markdown('''
            Uma análise dos dados da pandemia até o momento.
            ''') ,
         ]
    
    def __dash_est_mun(self):
        """
        montar a seleção de estados e municipios
        :return: None
        """
        opcao_municipio = [
            html.Label('Municípios', className='opcoes-label'),
            dcc.Dropdown(
                id='opcao_municipio',
                options=[
                    {'label': self.municipios_key[codmun], 'value': codmun}
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
                    {'label': self.estados_key[coduf], 'value': coduf}
                        for coduf in self.estados_key.index
                ],
                value=[33, 35, 76],
                multi=True
            ),
        ]
        
        opcoes_lista = [opcao_estado,
                        opcao_municipio
                        ]
        
        opcoes_est_mun = [
            html.Div(children=opcao, className='opcoes')
            for opcao in opcoes_lista
        ]
        
        self.dash_builder['est_mun'] = [
            dcc.Markdown('---'),
            html.Label('Seleção', className='secao-titulo'),
            html.Div(children=opcoes_est_mun,
                     style={'display': 'grid',
                            'grid-template-columns': 'repeat(2, 1fr)',
                            'grid-gap': '30px'
                            })
        ]
        
    def __dash_grafico(self):
        """

        :return: None
        """

        dropdown_xlog = dcc.Dropdown(
            id = 'xlog', className='axisTipo',
            options=[
                dict(label='log', value='log'),
                dict(label='lin', value='linear'),
            ],
            value='linear',
            clearable=False
        )
        
        dropdown_ylog = dcc.Dropdown(
            id = 'ylog', className='axisTipo',
            options=[
                dict(label='log', value='log'),
                dict(label='lin', value='linear'),
            ],
            value='log',
            clearable=False
        )

        fig = dcc.Graph(id='covid', figure=self.fig)
        
        self.dash_builder['grafico'] = [ html.Div(id='figdiv', children=[ fig, dropdown_xlog, dropdown_ylog ]) ]

    def __dash_opcoes(self):
        """

        :return: None
        """

        opcao_suavizacao = [
            html.Label('Suavização', className='opcoes-label'),
            dcc.RadioItems(
                id='opcao_suavizacao',
                options=[
                    {'label': 'Sem suavização', 'value': 0},
                    {'label': 'Média móvel de 3 dias', 'value': 3},
                    {'label': 'Média móvel de 5 dias', 'value': 5},
                    {'label': 'Média móvel de 7 dias', 'value': 7}
                ],
                value=7
            )
        ]

        opcao_obitos_casos = [
            html.Label('Óbitos ou casos', className='opcoes-label'),
            dcc.RadioItems(
                id='opcao_obitos_casos',
                options=[
                    {'label': 'Óbitos', 'value': 'obitos'},
                    {'label': 'Casos', 'value': 'casos'}
                ],
                value='obitos'
            )
        ]

        opcao_total_novos = [
            html.Label('# total ou # novos', className='opcoes-label'),
            dcc.RadioItems(
                id='opcao_total_novos',
                options=[
                    {'label': '# total', 'value': 'total'},
                    {'label': '# novos', 'value': 'novos'}
                ],
                value='total'
            )
        ]

        opcao_eixox_tempo = [
            html.Label('Eixo X: Tempo ou Atemporal', className='opcoes-label'),
            dcc.RadioItems(
                id='opcao_eixox_tempo',
                options=[
                    {'label': 'Tempo', 'value': 'tempo'},
                    {'label': 'Atemporal', 'value': 'atemporal'}
                ],
                value='tempo'
            )
        ]

        norm_obrig = dcc.RadioItems(
                id='opcao_norm_pop', className='opcoes-table',
                options= [
                    {'label': 'Sem norm. pop.', 'value': 0 },
                    {'label': 'Per capita', 'value': 'percapita'},
                    {'label': 'Por dens. demográf.', 'value': 'densidade_demografica' }
                ],
                value='percapita'
        )

        norm_extra = dcc.Checklist(
            id='opcao_norm_extra', className='opcoes-table',
            options=[
                {'label': '% idosos', 'value': 'perfil_demografico'}
            ],
            value=[]
        )

        norm_xy = dcc.Checklist(
            id='opcao_norm_xy', className='opcoes-table',
            options=[
                {'label': 'Eixo X', 'value': 'x'},
                {'label': 'Eixo Y', 'value': 'y'}
            ],
            value=['y']
        )

        opcao_eixos = [
            html.Label('Normalização', className='opcoes-label'),
            html.Div([
                html.Div([norm_obrig, norm_extra]),
                norm_xy
            ], style={'display': 'grid',
                      'grid-template-columns': 'repeat(2, 1fr)',
                        })

        ]

        opcoes_lista = [opcao_suavizacao,
                        opcao_obitos_casos, opcao_total_novos,
                        opcao_eixox_tempo,
                        opcao_eixos
                        ]

        opcoes_lista_div = [
            html.Div(children=opcao, className='opcoes')
            for opcao in opcoes_lista
        ]

        self.dash_builder['opcoes_grid'] = [
            html.Div('Opções', className='secao-titulo'),
            html.Div(children=opcoes_lista_div,
                     style={'display': 'grid',
                            'grid-template-columns': 'repeat(5, 1fr)',
                            'grid-gap': '30px'
                            })
        ]

    def __dash_debug(self):
        self.dash_builder['debug'] = [
            html.Label('Texto debug:'),
            html.Div(id='debug', children=''),
            html.Label('Botão Debug:'),
            html.Div(id='btndebug', children=''),
            html.Button('Clique aqui!', id='btn', n_clicks=0)
        ]

    def dash_build(self, debug=False):
        """
        construção do aplicativo Dash
        rodar todas as funções cujo nome começa por '__dash'
        :return: app
        """

        func_dash_build = [ v for k, v in self.__class__.__dict__.items()
                           if k.startswith('_covid_plot__dash') ] # mangling

        for f in func_dash_build:
            if 'debug' in f.__name__:
                if debug:
                    _ = f(self)
            else:
                _ = f(self)

        external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
        app = dash.Dash('covid',
                        external_stylesheets=external_stylesheets)
        app.title = 'COVID-19'
        app.layout = html.Div(children=ft.reduce(lambda x,y:x+y, self.dash_builder.values()))

        if debug:
            app.callback(
                Output(component_id='btndebug', component_property='children'),
                [Input(component_id='btn', component_property='n_clicks')],
                [State(component_id='covid', component_property='relayoutData')]
            )(self.dbg_btn)

        return app

    # dash app callback
    def atualizar_grafico(self, xlog, ylog,
                          data_estados, data_municipios,
                          obitos_casos, total_novos, tempo_atempo,
                          suavizacao,
                          normalizacao_pop, normalizacao_extra, norm_xy_list,
                          fig
                          ):
        """
        selecionar x e y com base nas opções
        :return: string x e y
        """
        x, y = self.selec_xy(obitos_casos, total_novos, tempo_atempo)

        # acessar figura antes da atualização para saber o estado dos botoes de escala dos eixos
        fig_old = fig

        # normalizacao
        normalizacao = normalizacao_extra
        if normalizacao_pop != 0:
            normalizacao += [ normalizacao_pop ]

        if len(normalizacao) == 0:
            normalizacao = None

        if len(norm_xy_list)>0:
            norm_xy = ft.reduce(lambda x,y:x+y, norm_xy_list)
        else:
            norm_xy = ''
        
        self.fig, self.df_norm, self.titulo = self.construir_figura(
            x=x, y=y,
            data_estados=data_estados, data_municipios=data_municipios,
            normalizacao=normalizacao, suavizacao=suavizacao,
            norm_xy=norm_xy
        )

        self.atualizar_figura(x, y, xlog, ylog, suavizacao=suavizacao,
                              obitos_casos=obitos_casos, tempo_atempo=tempo_atempo,
                              normalizacao_pop=normalizacao_pop,
                              data_estados=data_estados, data_municipios=data_municipios)
        
        # uirevision
        self.fig['layout']['uirevision']='none'

        return self.fig
    
    # dash app callback
    def escala_eixo(self, tempo_atempo, ylog, eixo_norm):
        """
        selecionar escala do eixo a depender das opções
        :param tempo_atempo: opção de eixo X temporal ou atemporal
        :param xlog: escala do eixo y
        :param eixo_norm: o qual eixo aplicar a normalização
        :return: dash.Output: xlog e eixo_norm
        """
        if tempo_atempo == 'tempo':
            xlog = 'linear'
            eixo_norm = list(frozenset(eixo_norm) - frozenset(['x']))
        
        else:
            xlog = ylog
            if 'y' in eixo_norm:
                eixo_norm = list(frozenset(eixo_norm) | frozenset(['x']))
        
        return xlog, eixo_norm
        

    def selec_xy(self, obitos_casos, total_novos, tempo_atempo):
        """
        Selecionar x e y com base nestes três parâmetros
        :param obitos_casos: se tratamos de óbitos ou casos de infecção
        :param total_novos: se tratamos de óbitos/casos totais ou novos
        :param tempo_atempo: se no eixo x plotamos em dias ou óbitos/casos
        :return: dois valores string de x e y
        """
        st = ''
        for s in [ obitos_casos, total_novos, tempo_atempo ]:
            st += s.lower()[0]

        return 'x_' + st, 'y_' + st

    def salvar(self, html_fig=None, img=None):
        """
        salvar as figuras
        :return: None
        """

        html_fig = r'..\..\imgs (nogit)\img.html'
        img = r'..\..\imgs (nogit)\img.png'

        if html_fig is not None:
            self.fig.write_html(html_fig)

        if img is not None:
            self.fig.write_image(img)

    def get_app_id(self, id):
        return self.dashapp.layout._get_set_or_delete(id=id, operation='get')

    def set_app_id(self, id, new):
        return self.dashapp.layout._get_set_or_delete(id=id, operation='set', new_item=new)

    # debug callback
    def dbg_btn(self, n_clicks, relayout):
        #fig = self.get_app_id(id='covid').figure
        fig = self.fig
        txt1 = fig['layout']['xaxis']['type'] or ''
        txt = 'Escala eixo X: ' + txt1 + '\\n'
        txt += r'\\n' + str(relayout)
        return txt

# carregar o cache ao inves de processar os dados
# br = covid.covid_brasil(diretorio = None, graficos = False)
br = covid.dumbcache_load(cache_dir=r'..\data\cache')

plt = covid_plot(br)

#if __name__ == '__main__':
if True:
    if os.environ.get('PYCHARM_HOSTED', default=0) == 0:
        plt.dashapp.run_server(debug=True)