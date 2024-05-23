import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
from distrito_federal_setor import setores

# Configurar o Selenium com Chrome e WebDriver Manager
chrome_options = Options()
chrome_options.add_argument("--headless")  # Executar em modo headless (sem abrir o navegador)
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

lista_de_imoveis = []

for pagina in range(1, 242):
    driver.get(f'https://www.dfimoveis.com.br/aluguel/df/todos/imoveis?pagina={pagina}')
    #time.sleep(5)  # Aumentar o tempo de espera para garantir que a página carregue

    # Capturar os links dos imóveis
    imoveis = driver.find_elements(By.CSS_SELECTOR, 'a.new-card')
    links_imoveis = [imovel.get_attribute('href') for imovel in imoveis]

    for link in links_imoveis:
        driver.get(link)
        #time.sleep(5)  # Aumentar o tempo de espera para garantir que a página carregue
        
        conteudo = driver.page_source
        site = BeautifulSoup(conteudo, 'html.parser')

        # Extração de informações adicionais dentro do anúncio
        try:
            titulo = site.find('h1', attrs={'class': 'mb-0 font-weight-600 fs-1-5'}).text.strip()
        except AttributeError:
            titulo = 'N/A'
        
        try:
            preco = site.find('small', attrs={'class': 'display-5 text-warning precoAntigoSalao'}).text.strip()
        except AttributeError:
            preco = 'N/A'
        
        # Filtrar preços inválidos
        if preco in ['N/A', 'Sob Consulta'] or not re.search(r'\d', preco):
            continue  # Pular este imóvel se o preço for inválido
        
        # Remover texto não numérico do preço
        preco = re.sub(r'[^\d,]', '', preco).replace(',', '.')

        try:
            imobiliaria = site.find('h6', attrs={'class': 'pb-0 mb-0'}).text.strip()
        except AttributeError:
            imobiliaria = 'N/A'
        
        try:
            subtitulo = site.find('p', attrs={'class': 'w-100 pb-3 mb-0 texto-descricao'}).text.strip()
        except AttributeError:
            subtitulo = 'N/A'
        
        try:
            area = site.find('small', attrs={'class': 'display-5 text-warning'}).text.strip()
        except AttributeError:
            area = 'N/A'
        
        try:
            detalhes_div = site.find('div', attrs={'class': 'row justify-content-between flex-row flex-nowrap mt-1 mb-2'})
            detalhes_itens = detalhes_div.find_all('small', attrs={'class': 'text-muted'})
            quarto = detalhes_itens[0].text.strip() if detalhes_itens else 'N/A'
            suite = detalhes_itens[1].text.strip() if len(detalhes_itens) > 1 else 'N/A'
            vaga = detalhes_itens[2].text.strip() if len(detalhes_itens) > 2 else 'N/A'
            cidade = detalhes_itens[3].text.strip() if len(detalhes_itens) > 3 else 'N/A'
        except AttributeError:
            quarto = suite = vaga = cidade = 'N/A'

        try:
            detalhe1 = site.find('h6', attrs={'class': 'text-normal mb-0'}).text.strip()
        except AttributeError:
            detalhe1 = 'N/A'

        try:
            memorial = site.find('small', text=re.compile('Memorial de Incorporação')).text.strip()
        except AttributeError:
            memorial = 'N/A'
        
        try:
            codigo = site.find('small', text=re.compile(r'\d{9}')).text.strip()
        except AttributeError:
            codigo = 'N/A'

        try:
            ultima_atualizacao = site.find('small', text=re.compile(r'\d{2}/\d{2}/\d{4}')).text.strip()
        except AttributeError:
            ultima_atualizacao = 'N/A'

        try:
            fase = site.find('h5', text=re.compile('Fase')).find('span').text.strip()
        except AttributeError:
            fase = 'N/A'

        try:
            caracteristicas_ul = site.find('ul', attrs={'class': 'checkboxes'})
            caracteristicas = [li.text.strip() for li in caracteristicas_ul.find_all('li')] if caracteristicas_ul else []
        except AttributeError:
            caracteristicas = []

        lista_de_imoveis.append([
            titulo, subtitulo, link, preco, area, quarto, suite, vaga, cidade,
            imobiliaria, detalhe1, memorial, codigo, ultima_atualizacao, fase, caracteristicas
        ])

# Fechar o driver
driver.quit()

# Criar o DataFrame
df_imovel = pd.DataFrame(lista_de_imoveis, columns=[
    'Título', 'Subtítulo', 'Link', 'Preço', 'Área', 'Quarto', 'Suite', 'Vaga', 'Cidade',
    'Imobiliária', 'Detalhe 1', 'Memorial de Incorporação', 'Código', 'Última Atualização', 'Fase', 'Características'
])

# Remover duplicatas com base na coluna 'Link'
df_imovel = df_imovel.drop_duplicates(subset='Link')

# Remover espaços em branco e substituir valores vazios por NaN
df_imovel['Preço'] = df_imovel['Preço'].str.replace(' ', '').replace('', np.nan)
df_imovel['Área'] = df_imovel['Área'].str.replace(' ', '').replace('', np.nan)

# Remover os pontos (separadores de milhares) da coluna 'Preço'
df_imovel['Preço'] = df_imovel['Preço'].str.replace('.', '')

# Remover linhas com valores nulos na coluna 'Preço'
df_imovel = df_imovel.dropna(subset=['Preço'])

# Convertendo a coluna 'Preço' para números
df_imovel['Preço'] = df_imovel['Preço'].str.replace(r'\D', '', regex=True).astype(float)

# Converter a coluna 'Área' para números
df_imovel['Área'] = df_imovel['Área'].str.replace(r'\D', '', regex=True).astype(float)

# Convertendo as colunas 'Quartos', 'Suítes' e 'Vagas' para números
df_imovel['Quarto'] = df_imovel['Quarto'].str.extract(r'(\d+)', expand=False).fillna('0').astype(int)
df_imovel['Suite'] = df_imovel['Suite'].str.extract(r'(\d+)', expand=False).fillna('0').astype(int)
df_imovel['Vaga'] = df_imovel['Vaga'].str.extract(r'(\d+)', expand=False).fillna('0').astype(int)

# Filtrar imóveis onde 'Preço' ou 'Área' são 0
df_imovel = df_imovel[(df_imovel['Preço'] != 0) & (df_imovel['Área'] != 0)]

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

# Adicionar nova coluna 'Tipo' ao DataFrame
df_imovel['Tipo'] = df_imovel['Link'].apply(extrair_tipo)

# Exportar o DataFrame para um arquivo Excel
df_imovel.to_excel(r'quinto_andar_05_2024.xlsx', index=False)
