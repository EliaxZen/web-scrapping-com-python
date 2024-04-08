from curses.ascii import alt
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
import time

inicio = time.time()

lista_de_imoveis = []
pagina = 1

# Headers customizados
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

# Usando sessões
with requests.Session() as s:
    s.headers.update(headers)


for pagina in range(1, 2200):
    url = f'https://www.imovelweb.com.br/casas-terrenos-rurais-comerciais-apartamentos-lancamentos-horizontais-lancamentos-verticais-lancamentos-horizontais-verticais-lotes-edificios-condominios-de-casas-condominios-de-edificios-lancamentos-na-praia-lancamentos-no-campo-lancamentos-comerciais-venda-distrito-federal-pagina-{pagina}.html'
    resposta = s.get(url)
    #  # Levanta um erro se a requisição falhar

    conteudo = resposta.content
    site = BeautifulSoup(conteudo, 'html.parser')
    imoveis = site.findAll('div', attrs={'data-qa': 'posting PROPERTY'})

    for imovel in imoveis:
        # Título do imóvel
        titulo = imovel.find('div', attrs={'class': 'sc-ge2uzh-0 eWOwnE postingAddress'})

        # Link do imovel
        link = 'https://www.imovelweb.com.br' + imovel['data-to-posting']

        # Subtítulo do imóvel
        subtitulo = imovel.find('h2', attrs={'data-qa': 'POSTING_CARD_LOCATION'})
        
        # Nome da Imobiliária
        imobiliaria_element = imovel.find('img', attrs={'data-qa': 'POSTING_CARD_PUBLISHER'})
        imobiliaria = imobiliaria_element['src'] if imobiliaria_element else None

        # Preco aluguel ou Venda
        preco = imovel.find('div', attrs={'data-qa': 'POSTING_CARD_PRICE'})
        
        # Preço Condominio
        condominio = imovel.find('div', attrs={'data-qa': 'expensas'}) 
        
        # Metro quadrado
        metro_area = imovel.find('h3', attrs={'data-qa': 'POSTING_CARD_FEATURES'})
        if metro_area is not None:
            metro = metro_area.find('span')

        
        # quartos, suíte, vagas
        quarto_banheiro_vaga = imovel.find('h3', attrs={'data-qa': 'POSTING_CARD_FEATURES'})
        if quarto_banheiro_vaga:
            lista = quarto_banheiro_vaga.findAll('span')
            quarto = banheiro = vaga = None

            for item in lista:
                if 'quartos' in item.text.lower():
                    quarto = item.text
                elif 'ban.' in item.text.lower():
                    banheiro = item.text
                elif 'vaga' in item.text.lower():
                    vaga = item.text
        else:
            quarto = banheiro = vaga = None
        
        # Append to list only if 'Metro Quadrado' is not a range and 'Preço' is not "R$ Sob Consulta"
        if titulo is not None and subtitulo is not None and preco is not None and metro is not None:
            lista_de_imoveis.append([titulo.text.strip(), subtitulo.text.strip(), link, preco.text, metro.text.replace(' m² tot.', '').strip(), quarto, banheiro, vaga, imobiliaria])
        

# Create DataFrame
df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo', 'Link', 'Preço','Metro Quadrado', 'Quarto', 'Banheiro', 'Vaga', 'Imobiliária'])

# Convertendo a coluna 'Preço' para números
# Substituir valores vazios por NaN na coluna de preço
df_imovel['Preço'].replace('', np.nan, inplace=True)

# Converter a coluna de preço para float
df_imovel['Preço'] = df_imovel['Preço'].astype(float)
df_imovel['Preço'] = df_imovel['Preço'].str.replace(r'\D', '', regex=True).astype(float)

# Substituir valores vazios por NaN
df_imovel['Metro Quadrado'] = df_imovel['Metro Quadrado'].replace('', np.nan)

# Converter a coluna 'Metro Quadrado' para números
df_imovel['Metro Quadrado'] = df_imovel['Metro Quadrado'].str.replace(r'\D', '', regex=True).astype(float)

# Convertendo as colunas 'Quartos', 'Suítes' e 'Vagas' para números
df_imovel['Quarto'] = df_imovel['Quarto'].str.extract(r'(\d+)', expand=False).fillna('0').astype(int)
df_imovel['Banheiro'] = df_imovel['Banheiro'].str.extract(r'(\d+)', expand=False).fillna('0').astype(int)
df_imovel['Vaga'] = df_imovel['Vaga'].str.extract(r'(\d+)', expand=False).fillna('0').astype(int)

# Add new column 'M2' and calculate the division
df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Metro Quadrado']


# Função para extrair o setor da string de título
def extrair_setor(titulo):
    # Lista de setores
    setores = [
        'ADE', 'SRTVS', 'STN', 'SMT', 'SRB', 'SRTVN', 'SQ', 'SQB', 'SQNW', 'SMI', 'SMS', 'SMSE', 'SMDB', 'SMHN', 'SHVG',
        'SIN', 'SMAS', 'SIA', 'SHTS', 'SHTN', 'SHLN', 'SHLS', 'SDN', 'SGCV', 'SHIP', 'SDS', 'QRI', 'QRO', 'QS', 'AE', 'AC', 
        'QSA', 'QSB', 'QSC', 'QSE', 'QSF', 'AV', 'AR', 'C', 'CNA', 'CNC', 'CND', 'CNF', 'CNG','CNM', 'CNN', 'CNR', 'CSA', 'CSC',
        'CSD', 'CSF' 'AeB', 'AEMN', 'AOS', 'APO', 'ARIE', 'AVPR', 'BOT', 'BSB', 'CA', 'CADF', 'CCSW', 'CEN', 'CES', 'CE-UnB', 'CL',
        'CLN', 'SAUS', 'SCSV', 'EQ','EQNL', 'EQNN', 'EQNP', 'EQSW' 'EQNO', 'CLRN', 'CLS', 'CLSW', 'CRN', 'CRS', 'EMI', 'EMO', 'EPAA',
        'EPAC', 'EPAR', 'EPCA', 'EPCL', 'EPCT', 'EPCV', 'EPDB',
        'EPGU', 'SCN', 'ES', 'EPIA', 'EPIB', 'EPIG', 'EPIP', 'EPJK', 'EPNA', 'QNH', 'QNJ', 'QNL', 'EPNB', 'EPPN', 'EPPR', 'EPTG',
        'EPTM', 'EPTT', 'EPUB', 'EPVB',
        'EPVL', 'QBR', 'QD', 'QMS', 'QNB', 'QNC', 'QND', 'QNE', 'QNF', 'EPVP', 'EQN', 'EQS', 'ERL', 'ERN', 'ERS', 'ERW', 'ESAF',
        'ETO', 'ML', 'PCH', 'PFB', 'PFR', 'PMU', 'PqEAT',
        'PqEB', 'PqEN', 'PqNB', 'PTP', 'QELC', 'QI', 'QL', 'QMSW', 'QRSW', 'RER-IBGE', 'SAAN', 'SAFN', 'SAFS', 'SAI', 'SO', 'SAIN',
        'SAIS', 'QNQ', 'QNR', 'SAM', 'SAN e SAUN', 'SAS e SAUS', 'SBN', 'SBS', 'SCEEN', 'SCEES', 'SCEN', 'SCES', 'SCIA', 'SCLRN', 'SCN',
        'SCRN', 'SCRS', 'SCS', 'SCTN', 'SCTS', 'SDC', 'SDMC', 'SDN', 'SDS', 'SEDB', 'SEN', 'SEPN', 'SEPS', 'SES', 'SEUPS',
        'SFA', 'SGA', 'SGAN', 'SGAP', 'SGAS', 'SGCV', 'SGMN', 'SGO', 'SGON', 'SHA', 'SHB', 'SHCES', 'SHCGN', 'SHCGS', 'SHCN',
        'SHCNW', 'SHCS', 'QOF', 'QRC', 'SHCSW', 'SHD', 'SHEP', 'SHIGS', 'SHIN', 'SHIP', 'SHIS', 'SHLN', 'SHLS', 'SHLSW', 'SHMA', 'SHN',
        'SHS', 'SHPS', 'SHSN', 'SHTN', 'SHTo', 'SHTQ', 'SHTS', 'SIA', 'SIBS', 'SIG', 'SIT', 'SMA', 'SMAN', 'SMAS', 'SMC',
        'SMDB', 'SMHN', 'SMHS', 'SMIN', 'SMLN', 'SMPW', 'SMU', 'SO', 'SOF', 'SOPI', 'SPLM', 'SPMN', 'SPO', 'SPP', 'SPVP',
        'SQN', 'SQNW', 'SQS', 'SQSW', 'SRES', 'SRIA', 'SRPN', 'SRPS', 'SRTVN', 'SRTVS', 'STN', 'STRC', 'STS', 'UnB', 'VPLA',
        'ZC', 'ZCA', 'ZE', 'ZfN', 'ZI', 'ZR', 'ZV', 'AE', 'AOS', 'CL', 'CLN', 'CLS', 'CLSW', 'CRS', 'EMI', 'EPDB', 'EPTG', 'EQN',
        'EQS', 'ML', 'QI', 'QL', 'QRSW', 'SAN', 'SAS', 'SBN', 'SBS', 'SCEN', 'SCES', 'SCLRN', 'SCN', 'SCS', 'SDN', 'SDS', 'SEN',
        'SEPN', 'SEPS', 'SES', 'SGAN', 'SGAS', 'SGON', 'SHIP', 'SHIN', 'SHIS', 'SHLN', 'SHLS', 'SHN', 'SHS', 'SHTN', 'SAIN', 'SAIS',
        'SIA', 'SIG', 'SMDB', 'SMHN', 'SMHS', 'SMLN', 'SMU', 'SQN', 'SQS', 'SQSW', 'SRTVN', 'SRTVS', 'QC', 'QE', 'SGCV', 'QN', 'EQRSW',
        'CLNW', 'QNP', 'QNO', 'QNA', 'CRNW', 'QR', 'CSG', 'QNG', 'CNB', 'QSD', 'QNN', 'CSB', 'QNM', 'ADE', 'AE', 'AeB', 'AEMN',
        'AOS', 'APO', 'ARIE', 'AVPR', 'BOT', 'BSB', 'CA', 'CADF', 'CCSW', 'CEN', 'CES', 'CE-UnB', 'CL','SHLN', 'SGCV',
        'CLN', 'CLRN', 'CLS', 'CLSW', 'CRN', 'CRS', 'EMI', 'EMO', 'EPAA', 'EPAC', 'EPAR', 'EPCA', 'EPCL', 'EPCT', 'EPCV', 'EPDB',
        'EPGU', 'EPIA', 'EPIB', 'EPIG', 'EPIP', 'EPJK', 'EPNA', 'EPNB', 'EPPN', 'EPPR', 'EPTG', 'EPTM', 'EPTT', 'EPUB', 'EPVB',
        'EPVL', 'EPVP', 'EQN', 'EQS', 'ERL', 'ERN', 'ERS', 'ERW', 'ESAF', 'ETO', 'ML', 'PCH', 'PFB', 'PFR', 'PMU', 'PqEAT',
        'PqEB', 'PqEN', 'PqNB', 'PTP', 'QELC', 'QI', 'QL', 'QMSW', 'QRSW', 'RER-IBGE', 'SAAN', 'SAFN', 'SAFS', 'SAI', 'SO', 'SAIN',
        'SAIS', 'SAM', 'SAN e SAUN', 'SAS e SAUS', 'SBN', 'SBS', 'SCEEN', 'SCEES', 'SCEN', 'SCES', 'SCIA', 'SCLRN', 'SCN',
        'SCRN', 'SCRS', 'SCS', 'SCTN', 'SCTS', 'SDC', 'SDMC', 'SDN', 'SDS', 'SEDB', 'SEN', 'SEPN', 'SEPS', 'SES', 'SEUPS',
        'SFA', 'SGA', 'SGAN', 'SGAP', 'SGAS', 'SGCV', 'SGMN', 'SGO', 'SGON', 'SHA', 'SHB', 'SHCES', 'SHCGN', 'SHCGS', 'SHCN',
        'SHCNW', 'SHCS', 'SHCSW', 'SHD', 'SHEP', 'SHIGS', 'SHIN', 'SHIP', 'SHIS', 'SHLN', 'SHLS', 'SHLSW', 'SHMA', 'SHN',
        'SHS', 'SHPS', 'SHSN', 'SHTN', 'SHTo', 'SHTQ', 'SHTS', 'SIA', 'SIBS', 'SIG', 'SIT', 'SMA', 'SMAN', 'SMAS', 'SMC',
        'SMDB', 'SMHN', 'SMHS', 'SMIN', 'SMLN', 'SMPW', 'SMU', 'SO', 'SOF', 'SOPI', 'SPLM', 'SPMN', 'SPO', 'SPP', 'SPVP',
        'SQN', 'SQNW', 'SQS', 'SQSW', 'SRES', 'SRIA', 'SRPN', 'SRPS', 'SRTVN', 'SRTVS', 'STN', 'STRC', 'STS', 'UnB', 'VPLA',
        'ZC', 'ZCA', 'ZE', 'ZfN', 'ZI', 'ZR', 'ZV', 'AE', 'AOS', 'CL', 'CLN', 'CLS', 'CLSW', 'CRS', 'EMI', 'EPDB', 'EPTG', 'EQN',
        'EQS', 'ML', 'QI', 'QL', 'QRSW', 'SAN', 'SAS', 'SBN', 'SBS', 'SCEN', 'SCES', 'SCLRN', 'SCN', 'SCS', 'SDN', 'SDS', 'SEN',
        'SEPN', 'SEPS', 'SES', 'SGAN', 'SGAS', 'SGON', 'SHIP', 'SHIN', 'SHIS', 'SHLN', 'SHLS', 'SHN', 'SHS', 'SHTN', 'SAIN', 'SAIS',
        'SIA', 'SIG', 'SMDB', 'SMHN', 'SMHS', 'SMLN', 'SMU', 'SQN', 'SQS', 'SQSW', 'SRTVN', 'SRTVS', 'QC', 'QE', 'SGCV', 'QN', 'EQRSW',
        'CLNW', 'QNP', 'QNO', 'QNA', 'CRNW', 'QR', 'CSG', 'QNG', 'CNB', 'QSD', 'QNN', 'CSB', 'QNM', 'CP', 'CCA', 'CSE', 'CRN', 'EPTC',
        'EPG', 'EPL', 'EPTC', 'EQPB', 'EQPR', 'EQS', 'EXPA', 'FCE', 'FCS', 'GAMA', 'GLS', 'ICC', 'IEA', 'IEMA', 'IEB', 'IECA', 'IEP',
        'IFB', 'IFC', 'IEAT', 'IPASE', 'LUM', 'MST', 'PLANO', 'PLANALTINA', 'PGS', 'PGC', 'PGS', 'PJA', 'PJG', 'PJF', 'PJC', 'PJB',
        'PJG', 'PJE', 'PLA', 'PLANO', 'PLC', 'PRG', 'REGA', 'RII', 'RII', 'RII', 'RII', 'RII', 'RMB', 'RPPN', 'SAB', 'SCM', 'SCR', 'SML',
        'SMO', 'STR', 'TNC', 'TRC', 'VNC', 'VNO', 'VNS', 'VND', 'VND', 'VNF', 'VNG', 'VNN', 'VP', 'VPP', 'VR', 'VRD', 'VSE', 'VSD', 'VSI', 
        'ZI', 'ZN', 'ZP', 'ZRB', 'ZRD', 'ZRL', 'ZRM', 'ZRN', 'ZRO', 'ZRP', 'ZRQ', 'ZRS', 'ZRU', 'ZRV', 'ZRW', 'ZRX', 'ZRY', 'ZSB', 'ZSC',
        'ZSE', 'ZSH', 'ZSJ', 'ZSK', 'ZSL', 'ZSM', 'ZSN', 'ZSO', 'ZSP', 'ZSQ', 'ZSR', 'ZSS', 'ZST', 'ZSU', 'ZSV', 'ZSW', 'ZSY', 'ZZ', 
        'DVO', 'IC', 'LIXO', 'PSR', 'RPA', 'RTI', 'SFE', 'SOL', 'TIB', 'VPS', 'VSI', 'VPJ', 'VPQ', 'ZEF', 'ZFM', 'ZVJ', 'ZAS', 'ZAU', 'ZCV', 
        'ZAC', 'ZAF', 'ZAX', 'ZCG', 'ZCR', 'ZET', 'ZGM', 'ZJP', 'ZLR', 'ZNT', 'ZPA', 'ZRA', 'ZSI', 'ZSZ', 'ZVV', 'ZVX', 'ZZL', 'ZAB', 'ZDF', 
        'ZOE', 'ZRA', 'ZRI', 'ZSD', 'ZSU', 'ZVE', 'ZVX', 'ZYZ', 'ZAM', 'ZAW', 'ZEL', 'ZRS', 'ZSB', 'ZVJ', 'ZVV', 'ZDA', 'ZRE', 'ZSL', 'ZSE', 
        'ZPP', 'ZRP', 'ZCI', 'ZI', 'ZRS', 'ZRW', 'ZSC', 'ZSY', 'ZVZ', 'ZSR', 'ZEM', 'ZUR', 'ZC', 'ZM', 'ZCX', 'ZMR', 'ZSL', 'ZLO', 'ZRE', 
        'ZUN', 'ZD', 'ZM', 'ZPP', 'ZVC', 'ZAU', 'ZSU', 'ZSE', 'ZVP', 'ZDA', 'ZVP', 'ZDD', 'ZAI', 'ZUP', 'ZBS', 'ZCR', 'ZGE', 'ZSC', 'ZSP', 
        'ZCL', 'ZVE', 'ZAM', 'ZVD', 'ZDL', 'ZCL', 'ZCP', 'ZUR', 'ZAA', 'ZCH', 'ZVI', 'ZVI', 'ZUZ', 'ZSS', 'ZVA', 'ZEM', 'ZEC', 'ZSB', 'ZMT',
        'ZAS', 'ZMD', 'ZMG', 'ZMB', 'ZMZ', 'ZMC', 'ZMB', 'ZMM', 'ZCE', 'ZME', 'ZUR', 'ZPA', 'ZEP', 'ZNI', 'ZMP', 'ZRM', 'ZRL', 'ZDN', 'ZMT',
        'ZDI', 'ZPP', 'ZCA', 'ZCP', 'ZRA', 'ZEM', 'ZPA', 'ZSL', 'ZSD', 'ZIS', 'ZTI', 'ZCT', 'ZPN', 'ZAN', 'ZEN', 'ZSN', 'ZST', 'ZNN', 'ZBN',
        'ZSD', 'ZPI', 'ZAI', 'ZSI', 'ZGI', 'ZNI', 'ZAA', 'ZAM', 'ZDN', 'ZLM', 'ZVD', 'ZET', 'ZLP', 'ZSU', 'ZSI', 'ZFI', 'ZAV', 'ZVL', 'ZSL',
        'ZRR', 'ZAC', 'ZTR', 'ZTN', 'ZUR', 'ZPC', 'ZRS', 'ZAE', 'ZRD', 'ZCP', 'ZEM', 'ZLM', 'ZVQ', 'ZSO', 'ZPA', 'ZFA', 'ZFA', 'ZAL', 'ZVL',
        'ZSD', 'ZAE', 'ZDI', 'ZSI', 'ZDO', 'ZLI', 'ZPI', 'ZSE', 'ZGE', 'ZIT', 'ZMT', 'ZRE', 'ZSE', 'ZMD', 'ZTP', 'ZEN', 'ZEM', 'ZCI', 'ZLI',
        'ZPR', 'ZVA', 'ZBR', 'ZTS', 'ZAT', 'ZLU', 'ZSO', 'ZES', 'ZFA', 'ZMI', 'ZPI', 'ZEC', 'ZMP', 'ZSI', 'ZEU', 'ZAP', 'ZMR', 'ZPM', 'ZFR',
        'ZSO', 'ZRT', 'ZSO', 'ZLO', 'ZRE', 'ZFA', 'ZRM', 'ZRP', 'ZAV', 'ZEC', 'ZEM', 'ZVI', 'ZPA', 'ZDA', 'ZLT', 'ZER', 'ZMA', 'ZRA', 'ZCD',
        'ZDP', 'ZEA', 'ZEA', 'ZCC', 'ZPD', 'ZLD', 'ZLS', 'ZLI', 'ZAC', 'ZMC', 'ZAV', 'ZRI', 'ZPA', 'ZLD', 'ZLO', 'ZDC', 'ZMV', 'ZSF', 'ZVE',
        'ZDM', 'ZDP', 'ZPV', 'ZDL', 'ZSR', 'ZSI', 'ZDR', 'ZSC', 'ZC', 'ZLS', 'ZDN', 'ZET', 'ZPA', 'ZSS', 'ZEN', 'ZSL', 'ZDV', 'ZEN', 'ZPV',
        'ZEM', 'ZDA', 'ZCD', 'ZEM', 'ZTR', 'ZPA', 'ZCN', 'ZCV', 'ZDP', 'ZEP', 'ZCP', 'ZPD', 'ZPC', 'ZCC', 'ZPC', 'ZPD', 'ZCG', 'ZRP', 'ZLV',
        'ZEA', 'ZAC', 'ZEA', 'ZPA', 'ZPS', 'ZDI', 'ZDP', 'ZDP', 'ZLI', 'ZLC', 'ZEA', 'ZLI', 'ZLT', 'ZAD', 'ZEC', 'ZET', 'ZVI', 'ZSI', 'ZDP',
        'ZLT', 'ZLT', 'ZRM', 'ZTI', 'ZPI', 'ZNI', 'ZTS', 'ZCS', 'ZPL', 'ZSD', 'ZVI', 'ZRP', 'ZDR', 'ZSA', 'ZEP', 'ZPM', 'ZPE', 'ZMC', 'ZEA',
        'ZLI', 'ZGE', 'ZSL', 'ZAC', 'ZAV', 'ZDR', 'ZTS', 'ZAV', 'ZDA', 'ZEN', 'ZEM', 'ZCD', 'ZDS', 'ZRV', 'ZPA', 'ZLD', 'ZDS', 'ZCN', 'ZCM',
        'ZAC', 'ZEC', 'ZDI', 'ZRP', 'ZEM', 'ZMS', 'ZVI', 'ZRI', 'ZRM', 'ZPO', 'ZTI', 'ZNI', 'ZTS', 'ZCS', 'ZPL', 'ZSD', 'ZVI', 'ZRP', 'ZDR',
        'ZSA', 'ZEP', 'ZPM', 'ZPE', 'ZMC', 'ZEA', 'ZLI', 'ZGE', 'ZSL', 'ZAC', 'ZAV', 'ZDR', 'ZTS', 'ZAV', 'ZDA', 'ZEN', 'ZEM', 'ZCD', 'ZDS',
        'ZRV', 'ZPA', 'ZLD', 'ZDS', 'ZCN', 'ZCM', 'ZAC', 'ZEC', 'ZDI', 'ZRP', 'ZEM', 'ZMS', 'ZVI', 'ZRI', 'ZRM', 'ZPO', 'ZTI', 'ZNI', 'ZTS',
        'ZCS', 'ZPL', 'ZSD', 'ZVI', 'ZRP', 'ZDR', 'ZSA', 'ZEP', 'ZPM', 'ZPE', 'ZMC', 'ZEA', 'ZLI', 'ZGE', 'ZSL', 'ZAC', 'ZAV', 'ZDR', 'ZTS',
        'ZAV', 'ZDA', 'ZEN', 'ZEM', 'ZCD', 'ZDS', 'ZRV', 'ZPA', 'ZLD', 'ZDS', 'ZCN', 'ZCM', 'ZAC', 'ZEC', 'ZDI', 'ZRP', 'ZEM', 'ZMS', 'ZVI',
        'ZRI', 'ZRM', 'ZPO', 'ZTI', 'ZNI', 'ZTS', 'ZCS', 'ZPL', 'ZSD', 'ZVI', 'ZRP', 'ZDR', 'ZSA', 'ZEP', 'ZPM', 'ZPE', 'ZMC', 'ZEA', 'ZLI',
        'ZGE', 'ZSL', 'ZAC', 'ZAV', 'ZDR', 'ZTS', 'ZAV', 'ZDA', 'ZEN', 'ZEM', 'ZCD', 'ZDS', 'ZRV', 'ZPA', 'ZLD', 'ZDS', 'ZCN', 'ZCM', 'ZAC',
        'ZEC', 'ZDI', 'ZRP', 'ZEM', 'ZMS', 'ZVI', 'ZRI', 'ZRM', 'ZPO', 'ZTI', 'ZNI', 'ZTS', 'ZCS', 'ZPL', 'ZSD', 'ZVI', 'ZRP', 'ZDR', 'ZSA',
        'ZEP', 'ZPM', 'ZPE', 'ZMC', 'ZEA', 'ZLI', 'ZGE', 'ZSL', 'ZAC', 'ZAV', 'ZDR', 'ZTS', 'ZAV', 'ZDA', 'ZEN', 'ZEM', 'ZCD', 'ZDS', 'ZRV',
        'ZPA', 'ZLD', 'ZDS', 'ZCN', 'ZCM', 'ZAC', 'ZEC', 'ZDI', 'ZRP', 'ZEM', 'ZMS', 'ZVI', 'ZRI', 'ZRM', 'ZPO', 'ZTI', 'ZNI', 'ZTS', 'ZCS',
        'ZPL', 'ZSD', 'ZVI', 'ZRP', 'ZDR', 'ZSA', 'ZEP', 'ZPM', 'ZPE', 'ZMC', 'ZEA', 'ZLI', 'ZGE', 'ZSL', 'ZAC', 'ZAV', 'ZDR', 'ZTS', 'ZAV',
        'ZDA', 'ZEN', 'ZEM', 'ZCD', 'ZDS', 'ZRV', 'ZPA', 'ZLD', 'ZDS', 'ZCN', 'ZCM', 'ZAC', 'ZEC', 'ZDI', 'ZRP', 'ZEM', 'ZMS', 'ZVI', 'ZRI',
        'ZRM', 'ZPO', 'ZTI', 'ZNI', 'ZTS', 'ZCS', 'ZPL', 'ZSD', 'ZVI', 'ZRP', 'ZDR', 'ZSA', 'ZEP', 'ZPM', 'ZPE', 'ZMC', 'ZEA', 'ZLI', 'ZGE',
        'ZSL', 'ZAC', 'ZAV', 'ZDR', 'ZTS', 'ZAV', 'ZDA', 'ZEN', 'ZEM', 'ZCD', 'ZDS', 'ZRV', 'ZPA', 'ZLD', 'ZDS', 'ZCN', 'ZCM', 'ZAC', 'ZEC',
        'ZDI', 'ZRP', 'ZEM', 'ZMS', 'ZVI', 'ZRI', 'ZRM', 'ZPO', 'ZTI', 'ZNI', 'ZTS', 'ZCS', 'ZPL', 'ZSD', 'ZVI', 'ZRP', 'ZDR', 'ZSA', 'ZEP',
        'ZPM', 'ZPE', 'ZMC', 'ZEA', 'ZLI', 'ZGE', 'ZSL', 'ZAC', 'ZAV', 'ZDR', 'ZTS', 'ZAV', 'ZDA', 'ZEN', 'ZEM', 'ZCD', 'ZDS', 'ZRV', 'ZPA',
        'ZLD', 'ZDS', 'ZCN', 'ZCM', 'ZAC', 'ZEC', 'ZDI', 'ZRP', 'ZEM', 'ZMS', 'ZVI', 'ZRI', 'ZRM', 'ZPO', 'ZTI', 'ZNI', 'ZTS', 'ZCS', 'ZPL',
        'ZSD', 'ZVI', 'ZRP', 'ZDR', 'ZSA', 'ZEP', 'ZPM', 'ZPE', 'ZMC', 'ZEA', 'ZLI', 'ZGE', 'ZSL', 'ZAC', 'ZAV', 'ZDR', 'ZTS', 'ZAV', 'ZDA',
        'ZEN', 'ZEM', 'ZCD', 'ZDS', 'ZRV', 'ZPA', 'ZLD', 'ZDS', 'ZCN', 'ZCM', 'ZAC', 'ZEC', 'ZDI', 'ZRP', 'ZEM', 'ZMS', 'ZVI', 'ZRI', 'ZRM',
        'ZPO', 'ZTI', 'ZNI', 'ZTS', 'ZCS', 'ZPL', 'ZSD', 'ZVI', 'ZRP', 'ZDR', 'ZSA', 'ZEP', 'ZPM', 'ZPE', 'ZMC', 'ZEA', 'ZLI', 'ZGE', 'ZSL',
        'ZAC', 'ZAV', 'ZDR', 'ZTS', 'ZAV', 'ZDA', 'ZEN', 'ZEM', 'ZCD', 'ZDS', 'ZRV', 'ZPA', 'ZLD', 'ZDS', 'ZCN', 'ZCM', 'ZAC', 'ZEC', 'ZDI',
        'ZRP', 'ZEM', 'ZMS', 'ZVI', 'ZRI', 'ZRM', 'ZPO', 'ZTI', 'ZNI', 'ZTS', 'ZCS', 'ZPL', 'ZSD', 'ZVI', 'ZRP', 'ZDR', 'ZSA', 'ZEP', 'ZPM',
        'ZPE', 'ZMC', 'ZEA', 'ZLI', 'ZGE', 'ZSL', 'ZAC', 'ZAV', 'ZDR', 'ZTS', 'ZAV', 'ZDA', 'ZEN', 'ZEM', 'ZCD', 'ZDS', 'ZRV', 'ZPA', 'ZLD',
        'ZDS', 'ZCN', 'ZCM', 'ZAC', 'ZEC', 'ZDI', 'ZRP', 'ZEM', 'ZMS', 'ZVI', 'ZRI', 'ZRM', 'ZPO', 'ZTI', 'ZNI', 'ZTS', 'ZCS', 'ZPL', 'ZSD',
        'ZVI', 'ZRP', 'ZDR', 'ZSA', 'ZEP', 'ZPM', 'ZPE', 'ZMC', 'ZEA', 'ZLI', 'ZGE', 'ZSL', 'ZAC', 'ZAV', 'ZDR', 'ZTS', 'ZAV', 'ZDA', 'ZEN',
        'ZEM', 'ZCD', 'ZDS', 'ZRV', 'ZPA', 'ZLD', 'ZDS', 'ZCN', 'ZCM', 'ZAC', 'ZEC', 'ZDI', 'ZRP', 'ZEM', 'ZMS', 'ZVI', 'ZRI', 'ZRM', 'ZPO',
        'ZTI', 'ZNI', 'ZTS', 'ZCS', 'ZPL', 'ZSD', 'ZVI', 'ZRP', 'ZDR', 'ZSA', 'ZEP', 'ZPM', 'ZPE', 'ZMC', 'ZEA', 'ZLI', 'ZGE', 'ZSL', 'ZAC',
        'ZAV', 'ZDR', 'ZTS', 'ZAV', 'ZDA', 'ZEN', 'ZEM', 'ZCD', 'ZDS', 'ZRV', 'ZPA', 'ZLD', 'ZDS', 'ZCN', 'ZCM', 'ZAC', 'ZEC', 'ZDI', 'ZRP',
        'ZEM', 'ZMS', 'ZVI', 'ZRI', 'ZRM', 'ZPO', 'ZTI', 'ZNI', 'ZTS', 'ZCS', 'ZPL', 'ZSD', 'ZVI', 'ZRP', 'ZDR', 'ZSA', 'ZEP', 'ZPM', 'ZPE',
        'ZMC', 'ZEA', 'ZLI', 'ZGE', 'ZSL', 'ZAC', 'ZAV', 'ZDR'
        ]

    # Remover duplicatas
    setores = list(set(setores))
    
    # Extrair as palavras individuais do título
    palavras = titulo.split()
    
    # Encontrar a primeira sigla que corresponde a um setor
    for palavra in palavras:
        if palavra in setores:
            return palavra
    
    # Se nenhuma sigla for encontrada, retornar 'OUTRO'
    return 'OUTRO'

# Aplicar a função para extrair o setor e criar a nova coluna 'Setor'
df_imovel['Setor'] = df_imovel['Título'].apply(extrair_setor)

# Exibir DataFrame com a nova coluna

# Write DataFrame to Excel file
df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\imovel_web\imovel_web_venda_df.xlsx', index=False)
fim = time.time()

tempo_total_segundos = fim - inicio

# Converter segundos para horas, minutos e segundos
horas = int(tempo_total_segundos // 3600)
tempo_total_segundos %= 3600
minutos = int(tempo_total_segundos // 60)
segundos = int(tempo_total_segundos % 60)

print(df_imovel)
print(resposta)
print("O script demorou", horas, "horas,", minutos, "minutos e", segundos, "segundos para ser executado.")