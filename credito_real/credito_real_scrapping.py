# CREDITO REAL

from curses.ascii import alt
from distrito_federal_setor import setores
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
import time

inicio = time.time()

lista_de_imoveis = []
passou_aqui = 0

# Headers customizados
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Referer': 'https://www.imovelweb.com.br/',
}

# Usando sessões
with requests.Session() as s:
    s.headers.update(headers)

for pagina in range(1, 10):
    passou_aqui += 1
    print(f'Passou aqui:{passou_aqui}')
    url = f'https://www.creditoreal.com.br/vendas?page={pagina}'
    try:
        resposta = s.get(url)
        resposta.raise_for_status()  # Levanta um erro se a requisição falhar
    except requests.exceptions.RequestException as e:
        print(f'Erro ao acessar a página: {e}')
        continue

    conteudo = resposta.content
    site = BeautifulSoup(conteudo, 'html.parser')
    imoveis = site.findAll('a', attrs={'class': 'sc-613ef922-1 iJQgSL'})

    for imovel in imoveis:
        # Título do imóvel
        titulo = imovel.find('span', attrs={'class': 'sc-e9fa241f-1 fdybXW'})

        # Link do imovel
        link = 'https://www.creditoreal.com.br' + imovel['href']

        # Subtítulo do imóvel
        subtitulo = imovel.find('span', attrs={'class': 'sc-e9fa241f-1 hqggtn'})
        
        # Tipo do Imóvel
        tipo = imovel.find('span', attrs={'class': 'sc-e9fa241f-0 bTpAju imovel-type'})

        # Preco aluguel ou Venda
        preco = imovel.find('p', attrs={'class': 'sc-e9fa241f-1 ericyj'})
        
        # Metro quadrado
        metro_area = imovel.find('div', attrs={'class': 'sc-b308a2c-2 iYXIja'})
        if metro_area is not None:
            metro = metro_area.find('p', attrs={'class': 'sc-e9fa241f-1 jUSYWw'})

        
        # quartos, vagas
        quarto_vaga = imovel.find('div', attrs={'class': 'sc-b308a2c-2 iYXIja'})
        if quarto_vaga:
            lista = quarto_vaga.findAll('p', attrs={'class': 'sc-e9fa241f-1 jUSYWw'})
            quarto = vaga = None

            for item in lista:
                if 'quartos' in item.text.lower():
                    quarto = item.text
                elif 'vaga' in item.text.lower():
                    vaga = item.text
        else:
            quarto = vaga = None
        
        # Append to list only if 'Metro Quadrado' is not a range and 'Preço' is not "R$ Sob Consulta"
        if titulo is not None and subtitulo is not None and preco is not None and metro is not None:
            lista_de_imoveis.append([titulo.text.strip(), subtitulo.text.strip(), link, preco.text, metro.text.replace(' m²', '').strip(), quarto, vaga, tipo.text])
        

# Create DataFrame
df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo', 'Link', 'Preço','Metro Quadrado', 'Quarto', 'Vaga', 'Tipo'])

# Remove o prefixo "R$" e quaisquer caracteres não numéricos da coluna "Preço"
df_imovel['Preço'] = df_imovel['Preço'].str.replace(r'R\$', '').str.replace(r'\D', '', regex=True)

# Converte a coluna para valores numéricos
df_imovel['Preço'] = pd.to_numeric(df_imovel['Preço'])

# Remova caracteres não numéricos da coluna "Metro Quadrado", "Quarto", "Banheiro" e "Vaga" e converta para valores numéricos
df_imovel['Metro Quadrado'] = df_imovel['Metro Quadrado'].str.extract(r'(\d+)').astype(float)
df_imovel['Quarto'] = df_imovel['Quarto'].str.extract(r'(\d+)').astype(float)
df_imovel['Vaga'] = df_imovel['Vaga'].str.extract(r'(\d+)').astype(float)


# Add new column 'M2' and calculate the division
df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Metro Quadrado']

# Substituir os valores vazios por 0 nas colunas especificadas
colunas_para_preencher = ['Preço', 'Metro Quadrado', 'Quarto', 'Vaga', 'M2']
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

# Write DataFrame to Excel file
df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\base_de_dados_excel\credito_real_data_base\credito_real_04_2024.xlsx', index=False)
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