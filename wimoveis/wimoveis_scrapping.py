from curses.ascii import alt
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
import time
from distrito_federal_setor import setores
inicio = time.time()

lista_de_imoveis = []
passou_aqui = 0

# Headers customizados
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

# Usando sessões
with requests.Session() as s:
    s.headers.update(headers)


for pagina in range(1, 191):
    passou_aqui += 1
    print(f'Passou aqui:{passou_aqui}')
    url = f'https://www.wimoveis.com.br/terrenos-lotes-venda-distrito-federal-pagina-{pagina}.html'
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

# Remove o prefixo "R$" e quaisquer caracteres não numéricos da coluna "Preço"
df_imovel['Preço'] = df_imovel['Preço'].str.replace(r'R\$', '').str.replace(r'\D', '', regex=True)

# Converte a coluna para valores numéricos
df_imovel['Preço'] = pd.to_numeric(df_imovel['Preço'])

# Remova caracteres não numéricos da coluna "Metro Quadrado", "Quarto", "Banheiro" e "Vaga" e converta para valores numéricos
df_imovel['Metro Quadrado'] = df_imovel['Metro Quadrado'].str.extract(r'(\d+)').astype(float)
df_imovel['Quarto'] = df_imovel['Quarto'].str.extract(r'(\d+)').astype(float)
df_imovel['Banheiro'] = df_imovel['Banheiro'].str.extract(r'(\d+)').astype(float)
df_imovel['Vaga'] = df_imovel['Vaga'].str.extract(r'(\d+)').astype(float)


# Add new column 'M2' and calculate the division
df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Metro Quadrado']

# Substituir os valores vazios por 0 nas colunas especificadas
colunas_para_preencher = ['Preço', 'Metro Quadrado', 'Quarto', 'Banheiro', 'Vaga', 'M2']
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

# Write DataFrame to Excel file
df_imovel.to_excel('wimoveis_scrapping_venda_lote_terreno_df_04_2024.xlsx', index=False)
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