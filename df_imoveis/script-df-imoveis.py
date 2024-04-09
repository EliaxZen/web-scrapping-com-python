from curses.ascii import alt
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np

lista_de_imoveis = []
passou_aqui = 0

for pagina in range(1, 242):
    passou_aqui += 1
    print(f'Url:{passou_aqui}')
    resposta = requests.get(f'https://www.dfimoveis.com.br/aluguel/df/todos/imoveis?pagina={pagina}')

    conteudo = resposta.content.decode('utf-8', 'replace')

    site = BeautifulSoup(conteudo, 'html.parser')

    # HTML do anúncio do imóvel
    imoveis = site.findAll('a', attrs={'class': 'new-card'})

    for imovel in imoveis:
        # Título do imóvel
        titulo = imovel.find('h2', attrs={'class': 'new-title'})

        # Link do imovel
        link = 'https://www.dfimoveis.com.br' + imovel['href']

        # Subtítulo do imóvel
        subtitulo = imovel.find('h3', attrs={'class': 'new-simple'})
        
        # Nome da Imobiliária
        imobiliaria_area = imovel.find('div', attrs={'class': 'new-anunciante'})
        imobiliaria = imobiliaria_area.find('img', alt=True)['alt']

        # Preco aluguel
        preco_area = imovel.find('div', attrs={'class': 'new-price'})
        preco = preco_area.find('h4')

        # Metro quadrado
        metro = imovel.find('li', attrs={'class': 'm-area'})
        
        # quartos, suíte, vagas
        quarto_suite_vaga = imovel.find('ul', attrs={'class': 'new-details-ul'})
        if quarto_suite_vaga:
            lista = quarto_suite_vaga.findAll('li')
            quarto = suite = vaga = None

            for item in lista:
                if 'quartos' in item.text.lower():
                    quarto = item.text
                elif 'suítes' in item.text.lower():
                    suite = item.text
                elif 'vagas' in item.text.lower():
                    vaga = item.text
        else:
            quarto = suite = vaga = None
        
        # Append to list only if 'Metro Quadrado' is not a range and 'Preço' is not "R$ Sob Consulta"
        if not ('a' in metro.text) and preco.text.strip() != "R$ Sob Consulta":
            lista_de_imoveis.append([titulo.text.strip(), subtitulo.text.strip(), link, preco.text, metro.text.replace('m²', '').strip(), quarto, suite, vaga, imobiliaria])

# Create DataFrame
df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo', 'Link', 'Preço','Metro Quadrado', 'Quarto', 'Suite', 'Vaga', 'Imobiliária'])

# Convertendo a coluna 'Preço' para números
df_imovel['Preço'] = df_imovel['Preço'].str.replace(r'\D', '', regex=True).astype(float)

# Substituir valores vazios por NaN
df_imovel['Metro Quadrado'] = df_imovel['Metro Quadrado'].replace('', np.nan)

# Converter a coluna 'Metro Quadrado' para números
df_imovel['Metro Quadrado'] = df_imovel['Metro Quadrado'].str.replace(r'\D', '', regex=True).astype(float)

# Convertendo as colunas 'Quartos', 'Suítes' e 'Vagas' para números
df_imovel['Quarto'] = df_imovel['Quarto'].str.extract(r'(\d+)', expand=False).fillna('0').astype(int)
df_imovel['Suite'] = df_imovel['Suite'].str.extract(r'(\d+)', expand=False).fillna('0').astype(int)
df_imovel['Vaga'] = df_imovel['Vaga'].str.extract(r'(\d+)', expand=False).fillna('0').astype(int)

# Add new column 'M2' and calculate the division
df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Metro Quadrado']


# Função para extrair o setor da string de título
def extrair_setor(titulo):
    # Lista de setores
    setores = [
        'PLANO PILOTO','GAMA','TAGUATINGA','BRAZLÂNDIA','SOBRADINHO','PLANALTINA','PARANOÁ','NÚCLEO BANDEIRANTE','CEILÂNDIA','GUARÁ','CRUZEIRO',
        'SAMAMBAIA','SANTA MARIA','SÃO SEBASTIÃO','RECANTO DAS EMAS','LAGO SUL','RIACHO FUNDO','LAGO NORTE','CANDANGOLÂNDIA','ÁGUAS CLARAS',
        'RIACHO FUNDO II','SUDOESTE/OCTOGONAL','VARJÃO','PARK WAY','SCIA','VICENTE PIRES','FERCAL'
        'ADE', 'SRTVS', 'STN', 'SMT', 'SRB', 'SRTVN', 'SQ', 'SQB', 'SQNW', 'SMI', 'SMS', 'SMSE', 'SMDB', 'SMHN', 'SHVG',
        'SIN', 'SMAS', 'SIA', 'SHTS', 'SHTN', 'SHLN', 'SHLS', 'SDN', 'SGCV', 'SHIP', 'SDS', 'QRI', 'QRO', 'QS', 'AE', 'AC', 
        'QSA', 'QSB', 'SHVP', 'QSC', 'QSE', 'QSF', 'AV', 'AR', 'C', 'CNA', 'CNC', 'CND', 'CNF', 'CNG','CNM', 'CNN', 'CNR', 'CSA', 'CSC',
        'CSD', 'CSF' 'AeB', 'AEMN', 'AOS', 'APO', 'ARIE', 'AVPR', 'BOT', 'BSB', 'CA', 'CADF', 'CCSW', 'CEN', 'CES', 'CE-UnB', 'CL',
        'CLN', 'SAUS', 'SCSV', 'EQ','EQNL', 'EQNN', 'EQNP', 'EQSW' 'EQNO', 'CLRN', 'CLS', 'CLSW', 'CRN', 'CRS', 'EMI', 'EMO', 'EPAA','EPAC', 'EPAR', 'EPCA', 'EPCL', 'EPCT', 'EPCV', 'EPDB',
        'EPGU', 'SCN', 'ES', 'EPIA', 'EPIB', 'EPIG', 'EPIP', 'EPJK', 'EPNA', 'QNH', 'QNJ', 'QNL', 'EPNB', 'EPPN', 'EPPR', 'EPTG',
        'EPTM', 'EPTT', 'EPUB', 'EPVB','EPVL', 'QBR', 'QD', 'QMS', 'QNB', 'QNC', 'QND', 'QNE', 'QNF', 'EPVP', 'EQN', 'EQS', 'ERL', 'ERN', 'ERS', 'ERW', 'ESAF','ETO', 'ML', 'PCH', 'PFB', 'PFR', 'PMU', 'PqEAT',
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
        'SEPN','SCLN', 'SEPS', 'SES', 'SGAN', 'SGAS', 'SGON', 'SHIP', 'SHIN', 'SHIS', 'SHLN', 'SHLS', 'SHN', 'SHS', 'SHTN', 'SAIN', 'SAIS',
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
    palavras_upper = [palavra.upper() for palavra in palavras]
    # Encontrar a primeira sigla que corresponde a um setor
    for palavra in palavras_upper:
        if palavra in setores:
            return palavra
    
    # Se nenhuma sigla for encontrada, retornar 'OUTRO'
    return 'OUTRO'

# Aplicar a função para extrair o setor e criar a nova coluna 'Setor'
df_imovel['Setor'] = df_imovel['Título'].apply(extrair_setor)

# Exibir DataFrame com a nova coluna
print(df_imovel)

# Write DataFrame to Excel file
df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\df_imoveis\df_imoveis_df_aluguel_04_2024.xlsx', index=False)

