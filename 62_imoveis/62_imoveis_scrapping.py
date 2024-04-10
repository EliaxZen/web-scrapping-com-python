from curses.ascii import alt
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np

from distrito_federal_setor import setores

lista_de_imoveis = []
passou_aqui = 0

for pagina in range(1, 1221):
    passou_aqui += 1
    print(f'Url:{passou_aqui}')
    resposta = requests.get(f'https://www.62imoveis.com.br/venda/go/todos/imoveis?pagina={pagina}')

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

# Exibir DataFrame com a nova coluna
print(df_imovel)

# Write DataFrame to Excel file
df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\62_imoveis\62_imoveis_GO_venda_04_2024.xlsx', index=False)

