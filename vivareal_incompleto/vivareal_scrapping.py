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

# Loop para acessar apenas a página 1
for pagina in range(1, 100):
    passou_aqui += 1
    print(f'Passou aqui:{passou_aqui}')
    url = f'https://www.vivareal.com.br/venda/distrito-federal/brasilia/?pagina={pagina}'
    try:
        resposta = s.get(url)
        resposta.raise_for_status()  # Levanta um erro se a requisição falhar
    except requests.exceptions.RequestException as e:
        print(f'Erro ao acessar a página: {e}')
        continue

    conteudo = resposta.content
    site = BeautifulSoup(conteudo, 'html.parser')

    # Encontrando todos os elementos HTML que representam os anúncios de imóveis
    imoveis = site.findAll('a', attrs={'class': 'property-card__content-link js-card-title'})

    for imovel in imoveis:
        # Título do imóvel
        titulo = imovel.find('span', attrs={'class': 'property-card__address'})

        # Link do imovel
        link = 'https://www.vivareal.com.br/' + imovel['href']

        # Subtítulo do imóvel
        subtitulo = imovel.find('span', attrs={'class': 'property-card__title js-cardLink js-card-title'})

        # Preco aluguel ou Venda
        preco = imovel.find('div', attrs={'class': 'property-card__price js-property-card-prices js-property-card__price-small'})
        
        # Metro quadrado
        metro_area = imovel.find('li', attrs={'class': 'property-card__detail-item property-card__detail-area'})
        if metro_area is not None:
            metro = metro_area.find('span')
        
        quarto_area = imovel.find('li', attrs={'class': 'property-card__detail-item property-card__detail-room js-property-detail-rooms'})
        quarto = quarto_area.find('span', attrs={'class': 'property-card__detail-value js-property-card-value'})
        quarto_texto = quarto.text.strip() if quarto else None

        banheiro_area = imovel.find('li', attrs={'class': 'property-card__detail-item property-card__detail-bathroom js-property-detail-bathroom'})
        banheiro = banheiro_area.find('span', attrs={'class': 'property-card__detail-value js-property-card-value'})
        banheiro_texto = banheiro.text.strip() if banheiro else None

        vaga_area = imovel.find('li', attrs={'class': 'property-card__detail-item property-card__detail-garage js-property-detail-garages'})
        vaga = vaga_area.find('span', attrs={'class': 'property-card__detail-value js-property-card-value'})
        vaga_texto = vaga.text.strip() if vaga else None

        variaveis_dumizaveis = imovel.find('ul', attrs={'class': 'property-card__amenities'})
        variaveis_dumizaveis_texto = variaveis_dumizaveis.text.strip() if variaveis_dumizaveis else None
        
        # Append to list only if 'Metro Quadrado' is not a range and 'Preço' is not "R$ Sob Consulta"
        if titulo is not None and subtitulo is not None and preco is not None and metro is not None:
            lista_de_imoveis.append([titulo.text.strip(), subtitulo.text.strip(), link, preco.text, metro.text.replace(' m² tot.', '').strip(), quarto, banheiro, vaga])
        

# Create DataFrame
df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo', 'Link', 'Preço','Metro Quadrado', 'Quarto', 'Banheiro', 'Vaga'])

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
df_imovel['Tipo do Imóvel'] = df_imovel['Link'].apply(extrair_tipo)

# Write DataFrame to Excel file
df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\vivareal_incompleto\imovel.xlsx', index=False)
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

