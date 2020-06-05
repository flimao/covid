#!/usr/env/python3
# -*- coding: utf-8 -*-

import pandas as pd
import os

class comorbidades:
    """
    Processa comorbidades
    """

    def __init__(self, diretorio=None):

        # se diretorio for None, corresponde ao diretorio raiz do script
        if diretorio is None:
            diretorio = r'..'
        
        # dar nome aos datasets
        datasets = { var: csv for var, csv in zip(
            ['diabetes_men', 'diabetes_women', 'bp', 'bmi_stats', 'bmi_child', 'bmi_age_men', 'bmi_age_women'],
            [r'NCD-RisC_Lancet_2016_Diabetes_Men_Agespecific_Prevalence_by_Country.csv',
            r'NCD-RisC_Lancet_2016_Diabetes_Women_Agespecific_Prevalence_by_Country.csv',
            r'NCD-RisC_Lancet_2017_Agespecific_BP_by_Country.csv',
            r'NCD_RisC_Lancet_2017_BMI_age_standardised_country.csv',
            r'NCD_RisC_Lancet_2017_BMI_child_adolescent_country.csv',
            r'NCD_RisC_Lancet_2017_mean_BMI_male_age_specific_country_estimates.csv',
            r'NCD_RisC_Lancet_2017_mean_BMI_female_age_specific_country_estimates.csv']
        ) }
        
        # criar dicionario com nomes
        for var, csv in datasets.items():
            self.__dict__[var] = self.ler_dados(diretorio, csv, datadir='NCD-RisC')
        
        # pre-processar (renomear colunas, etc)
        self.preproc()

    def ler_dados(self, diretorio, csv, datadir='NCD_RisC'):
        """
        ler os dados de comorbidades no brasil e no mundo
        
        :param diretorio: o diretório contendo os arquivos csv
        :param csv: o caminho para o arquivo csv
        :return: dataframe contendo as informações dos arquivos
        """
        
        DATAFILE_io = os.path.join(diretorio, r'data', datadir, csv)
        
        return pd.read_csv(DATAFILE_io, encoding='windows-1252')
    
    def preproc(self):
        """
        pre-processamento dos dados
        rodar todas as funções cujo nome começa por '__preproc'
        :return: None
        """

        func_mask = '_' + self.__class__.__name__ + '__preproc_' # mangling
        func_name_len = len(func_mask) - len('_' + self.__class__.__name__)
        
        func_preproc = [v for k, v in self.__class__.__dict__.items()
                        if k.startswith(func_mask)]
    
        for f in func_preproc:
            self.__dict__[f.__name__[func_name_len:]] = f(self)

    def __preproc_bmi_stats(self):
        """
        pré-processamento do dataset de estatísticas de BMI (idade agregada)
        :return: df pré-processado
        """
        
        df = self.bmi_stats
        dict_rename = {old: new for old, new in zip(df.columns,
                        ['country', 'iso', 'sex', 'year', 'bmi_mean', 'bmi_mean_95ICl',
                         'bmi_mean_95ICu',
                         'bmi_over30', 'bmi_over30_95ICl', 'bmi_over30_95ICu',
                         'bmi_over35', 'bmi_over35_95ICl', 'bmi_over35_95ICu',
                         'bmi_under18', 'bmi_under18_95ICl', 'bmi_under18_95ICu',
                         'bmi_btw18_20', 'bmi_btw18_20_95ICl', 'bmi_btw18_20_95ICu',
                         'bmi_btw20_25', 'bmi_btw20_25_95ICl', 'bmi_btw20_25_95ICu',
                         'bmi_btw25_30', 'bmi_btw25_30_95ICl', 'bmi_btw25_30_95ICu',
                         'bmi_btw30_35', 'bmi_btw30_35_95ICl', 'bmi_btw30_35_95ICu',
                         'bmi_btw35_40', 'bmi_btw35_40_95ICl', 'bmi_btw35_40_95ICu',
                         'bmi_over40', 'bmi_over40_95ICl', 'bmi_over40_95ICu']
        )}

        return df.rename(columns=dict_rename)
    
    def __preproc_diabetes_men(self):
        """
        pré-processamento do dataset de diabetes (masculino, separado por idade, ano e país)
        :return: df pré-processado
        """
        pass
    
    def __preproc_diabetes_women(self):
        """
        pré-processamento do dataset de diabetes (feminino, separado por idade, ano e país)
        :return: df pré-processado
        """
        pass
    
    def __preproc_bp(self):
        """
        pré-processamento do dataset de pressão arterial (separado por idade, ano e país)
        :return: df pré-processado
        """
        pass
    
    def __preproc_bmi_child(self):
        """
        pré-processamento do dataset de estatísticas de BMI (crianças e adolescentes)
        :return: df pré-processado
        """
        pass
    
    def __preproc_bmi_age_men(self):
        """
        pré-processamento do dataset de estatísticas de BMI (masculino, separado por idade)
        :return: df pré-processado
        """
        pass
    
    def __preproc_bmi_age_women(self):
        """
        pré-processamento do dataset de estatísticas de BMI (feminino, separado por idade)
        :return: df pré-processado
        """
        pass

cm = comorbidades()