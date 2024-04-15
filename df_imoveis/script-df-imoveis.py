from curses.ascii import alt
from distrito_federal_setor import setores
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np

lista_de_imoveis = []
passou_aqui = 0

for pagina in range(1, 243):
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

# Substituir os valores vazios por 0 nas colunas especificadas
colunas_para_preencher = ['Preço', 'Metro Quadrado', 'Quarto', 'Suite', 'Vaga', 'M2']
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
    if 'apartamento' in link:
        return 'Apartamento'
    elif 'casa' in link:
        return 'Casa'
    elif 'casa-condominio' in link:
        return 'Casa Condomínio'
    elif 'galpo' in link:
        return 'Galpão'
    elif 'garagem' in link:
        return 'Garagem'
    elif 'hotel-flat' in link:
        return 'Flat'
    elif 'flat' in link:
        return 'Flat'
    elif 'kitnet' in link:
        return 'Kitnet'
    elif 'loja' in link:
        return 'Loja'
    elif 'loteamento' in link:
        return 'Loteamento'
    elif 'lote-terreno' in link:
        return 'Lote Terreno'
    elif 'ponto-comercial' in link:
        return 'Ponto Comercial'
    elif 'prdio' in link or 'predio' in link:
        return 'Prédio'
    elif 'sala' in link:
        return 'Sala'
    else:
        return 'OUTROS'

# Adicionar uma coluna 'Tipo do Imóvel' ao DataFrame e preenchê-la com os tipos extraídos dos links
df_imovel['Tipo do Imóvel'] = df_imovel['Link'].apply(extrair_tipo)

# Exibir DataFrame com a nova coluna
print(df_imovel)

# Write DataFrame to Excel file
df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\base_de_dados_excel\df_imoveis_data_base\df_imoveis_df_aluguel_04_2024.xlsx', index=False)

