import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
from distrito_federal_setor import setores
import re
import numpy as np

# Configurar o Selenium com Chrome e WebDriver Manager
chrome_options = Options()
#chrome_options.add_argument("--headless")  # Executar em modo headless (sem abrir o navegador)
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

lista_de_imoveis = []

for pagina in range(1, 300):
    driver.get(f'https://www.dfimoveis.com.br/lancamento/df/todos/imoveis?pagina={pagina}')
    time.sleep(5)  # Aumentar o tempo de espera para garantir que a página carregue

    # Capturar os links dos imóveis
    imoveis = driver.find_elements(By.CSS_SELECTOR, 'a.new-card')
    links_imoveis = [imovel.get_attribute('href') for imovel in imoveis]

    for link in links_imoveis:
        driver.get(link)
        time.sleep(5)  # Aumentar o tempo de espera para garantir que a página carregue
        
        conteudo = driver.page_source
        site = BeautifulSoup(conteudo, 'html.parser')

        # Extração de informações adicionais dentro do anúncio
        try:
            titulo = site.find('h1', attrs={'class': 'titulo-imovel'}).text.strip()
        except AttributeError:
            titulo = 'N/A'
        
        try:
            subtitulo = site.find('h2', attrs={'class': 'subtitulo-imovel'}).text.strip()
        except AttributeError:
            subtitulo = 'N/A'
        
        try:
            preco = site.find('div', attrs={'class': 'preco-imovel'}).text.strip()
        except AttributeError:
            preco = 'N/A'
        
        try:
            area = site.find('span', attrs={'class': 'area-imovel'}).text.strip()
        except AttributeError:
            area = 'N/A'
        
        detalhes = site.find_all('li', attrs={'class': 'detalhes-imovel'})
        quarto = suite = vaga = None
        for detalhe in detalhes:
            if 'quartos' in detalhe.text.lower():
                quarto = detalhe.text
            elif 'suítes' in detalhe.text.lower():
                suite = detalhe.text
            elif 'vagas' in detalhe.text.lower():
                vaga = detalhe.text

        try:
            imobiliaria = site.find('div', attrs={'class': 'imobiliaria'}).text.strip()
        except AttributeError:
            imobiliaria = 'N/A'

        lista_de_imoveis.append([titulo, subtitulo, link, preco, area, quarto, suite, vaga, imobiliaria])

# Fechar o driver
driver.quit()

# Criar o DataFrame
df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo', 'Link', 'Preço', 'Área', 'Quarto', 'Suite', 'Vaga', 'Imobiliária'])

# Remover duplicatas com base na coluna 'Link'
df_imovel = df_imovel.drop_duplicates(subset='Link')

# Convertendo a coluna 'Preço' para números
df_imovel['Preço'] = df_imovel['Preço'].str.replace(r'\D', '', regex=True).astype(float)

# Substituir valores vazios por NaN
df_imovel['Área'] = df_imovel['Área'].replace('', np.nan)

# Converter a coluna 'Área' para números
df_imovel['Área'] = df_imovel['Área'].str.replace(r'\D', '', regex=True).astype(float)

# Convertendo as colunas 'Quartos', 'Suítes' e 'Vagas' para números
df_imovel['Quarto'] = df_imovel['Quarto'].str.extract(r'(\d+)', expand=False).fillna('0').astype(int)
df_imovel['Suite'] = df_imovel['Suite'].str.extract(r'(\d+)', expand=False).fillna('0').astype(int)
df_imovel['Vaga'] = df_imovel['Vaga'].str.extract(r'(\d+)', expand=False).fillna('0').astype(int)

# Adicionar nova coluna 'M2' e calcular a divisão
df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Área']

# Substituir os valores vazios por 0 nas colunas especificadas
colunas_para_preencher = ['Preço', 'Área', 'Quarto', 'Suite', 'Vaga', 'M2']
df_imovel[colunas_para_preencher] = df_imovel[colunas_para_preencher].fillna(0)

# Função para extrair o setor da string de título
def extrair_setor(titulo): 
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

# Função para extrair o tipo do imóvel do link
def extrair_tipo(link):
    if "apartamento" in link:
        return "Apartamento"
    elif "casa" in link:
        return "Casa"
    elif "casa-condominio" in link:
        return "Casa Condomínio"
    elif "galpo" in link:
        return "Galpão"
    elif "garagem" in link:
        return "Garagem"
    elif "hotel-flat" in link:
        return "Flat"
    elif "flat" in link:
        return "Flat"
    elif "kitnet" in link:
        return "Kitnet"
    elif "loja" in link:
        return "Loja"
    elif "loteamento" in link:
        return "Loteamento"
    elif "lote-terreno" in link:
        return "Lote Terreno"
    elif "ponto-comercial" in link:
        return "Ponto Comercial"
    elif "prdio" in link or "predio" in link:
        return "Prédio"
    elif "sala" in link:
        return "Sala"
    elif "rural" in link:
        return "Zona Rural"
    elif "lancamento" in link:
        return "Lançamento"
    else:
        return "OUTROS"

# Adicionar uma coluna 'Tipo do Imóvel' ao DataFrame e preenchê-la com os tipos extraídos dos links
df_imovel['Tipo'] = df_imovel['Link'].apply(extrair_tipo)

# Exibir DataFrame com a nova coluna
print(df_imovel)

# Write DataFrame to Excel file
df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\base_de_dados_excel\df_imoveis_data_base\df_imoveis_df_lancamento_05_2024.xlsx', index=False)
