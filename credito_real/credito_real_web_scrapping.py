from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
import time
import logging
import concurrent.futures
import requests

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Headers customizados
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Referer': 'https://www.imovelweb.com.br/',
}

def configure_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    return session

def extract_page_data(session, page):
    url = f'https://www.creditoreal.com.br/vendas?page={page}'
    try:
        response = session.get(url)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f'Erro ao acessar a página {page}: {e}')
        return None

def parse_imovel(imovel):
    titulo = imovel.find('span', attrs={'class': 'sc-e9fa241f-1 fdybXW'})
    link = 'https://www.creditoreal.com.br' + imovel['href']
    subtitulo = imovel.find('span', attrs={'class': 'sc-e9fa241f-1 hqggtn'})
    tipo = imovel.find('span', attrs={'class': 'sc-e9fa241f-0 bTpAju imovel-type'})
    preco = imovel.find('p', attrs={'class': 'sc-e9fa241f-1 ericyj'})
    
    metro_area = imovel.find('div', attrs={'class': 'sc-b308a2c-2 iYXIja'})
    if metro_area is not None:
        metro = metro_area.find('p', attrs={'class': 'sc-e9fa241f-1 jUSYWw'})
        if metro:
            metro_text = metro.text.strip()
            if 'hectares' in metro_text.lower():
                metro_value = float(re.search(r'(\d+)', metro_text).group(1)) * 10000
            else:
                metro_value = float(re.search(r'(\d+)', metro_text).group(1))
        else:
            metro_value = None
    else:
        metro_value = None

    quarto_vaga = imovel.find('div', attrs={'class': 'sc-b308a2c-2 iYXIja'})
    quarto = vaga = None
    if quarto_vaga:
        lista = quarto_vaga.findAll('p', attrs={'class': 'sc-e9fa241f-1 jUSYWw'})
        for item in lista:
            if 'quartos' in item.text.lower():
                quarto = re.search(r'(\d+)', item.text).group(1)
            elif 'vaga' in item.text.lower():
                vaga = re.search(r'(\d+)', item.text).group(1)
    
    if titulo and subtitulo and preco and metro_value:
        preco_value = re.sub(r'\D', '', preco.text)
        if preco_value and metro_value:
            return [titulo.text.strip(), subtitulo.text.strip(), link, preco_value, metro_value, quarto, vaga, tipo.text]
    return None

def process_page_content(content):
    site = BeautifulSoup(content, 'html.parser')
    imoveis = site.findAll('a', attrs={'class': 'sc-613ef922-1 iJQgSL'})
    data = [parse_imovel(imovel) for imovel in imoveis]
    return [item for item in data if item]

def main():
    inicio = time.time()
    session = configure_session()
    all_data = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(extract_page_data, session, page): page for page in range(1, 3440)}
        for future in concurrent.futures.as_completed(futures):
            content = future.result()
            if content:
                all_data.extend(process_page_content(content))

    df_imovel = pd.DataFrame(all_data, columns=['Título', 'Subtítulo', 'Link', 'Preço', 'Metro Quadrado', 'Quarto', 'Vaga', 'Tipo'])

    # Converte as colunas para valores numéricos, preenchendo com NaN onde não for possível
    df_imovel['Preço'] = pd.to_numeric(df_imovel['Preço'], errors='coerce')
    df_imovel['Metro Quadrado'] = pd.to_numeric(df_imovel['Metro Quadrado'], errors='coerce')
    df_imovel['Quarto'] = pd.to_numeric(df_imovel['Quarto'], errors='coerce')
    df_imovel['Vaga'] = pd.to_numeric(df_imovel['Vaga'], errors='coerce')

    # Add new column 'M2' and calculate the division
    df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Metro Quadrado']

    # Remover linhas onde 'Preço' ou 'Metro Quadrado' são 0, nulos ou vazios
    df_imovel.dropna(subset=['Preço', 'Metro Quadrado'], inplace=True)
    df_imovel = df_imovel[(df_imovel['Preço'] != 0) & (df_imovel['Metro Quadrado'] != 0)]
    
    # Substituir os valores vazios por 0 nas colunas especificadas
    colunas_para_preencher = ["Preço", "Metro Quadrado", "Quarto", "Vaga", "M2"]
    df_imovel[colunas_para_preencher] = df_imovel[colunas_para_preencher].fillna(0)

    # Write DataFrame to Excel file
    df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\base_de_dados_excel\credito_real_data_base\credito_real_venda_06_2024.xlsx', index=False)

    fim = time.time()
    tempo_total_segundos = fim - inicio
    horas = int(tempo_total_segundos // 3600)
    tempo_total_segundos %= 3600
    minutos = int(tempo_total_segundos // 60)
    segundos = int(tempo_total_segundos % 60)

    logging.info(f'O script demorou {horas} horas, {minutos} minutos e {segundos} segundos para ser executado.')

if __name__ == '__main__':
    main()