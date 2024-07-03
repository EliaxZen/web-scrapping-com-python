from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
import time
import logging
import concurrent.futures
import requests
from tqdm import tqdm

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Headers customizados
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Referer': 'https://www.creditoreal.com.br',
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
    try:
        titulo = imovel.find('span', class_='sc-e9fa241f-1 fdybXW').text.strip()
        link = 'https://www.creditoreal.com.br' + imovel['href']
        subtitulo = imovel.find('span', class_='sc-e9fa241f-1 hqggtn').text.strip()
        tipo = imovel.find('span', class_='sc-e9fa241f-0 bTpAju imovel-type').text.strip()
        preco = re.sub(r'\D', '', imovel.find('p', class_='sc-e9fa241f-1 ericyj').text)
        metro_text = imovel.find('div', class_='sc-b308a2c-2 iYXIja').find('p', class_='sc-e9fa241f-1 jUSYWw').text.strip()

        if 'hectares' in metro_text.lower():
            metro_value = float(re.search(r'(\d+)', metro_text).group(1)) * 10000
        else:
            metro_value = float(re.search(r'(\d+)', metro_text).group(1))

        quarto_vaga = imovel.findAll('p', class_='sc-e9fa241f-1 jUSYWw')
        quarto = vaga = None
        for item in quarto_vaga:
            if 'quartos' in item.text.lower():
                quarto = re.search(r'(\d+)', item.text).group(1)
            elif 'vaga' in item.text.lower():
                vaga = re.search(r'(\d+)', item.text).group(1)

        return [titulo, subtitulo, link, preco, metro_value, quarto, vaga, tipo]
    except AttributeError:
        return None

def process_page_content(content):
    site = BeautifulSoup(content, 'html.parser')
    imoveis = site.findAll('a', class_='sc-613ef922-1 iJQgSL')
    return [parse_imovel(imovel) for imovel in imoveis if parse_imovel(imovel)]

def main():
    # Definir o número de páginas para iterar e o número de imóveis desejados
    num_paginas = 3424  # Altere esse valor conforme necessário
    num_imoveis_desejados = 61608  # Altere esse valor conforme necessário

    inicio = time.time()
    session = configure_session()
    all_data = []
    total_imoveis = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(extract_page_data, session, page): page for page in range(1, num_paginas + 1)}
        
        # Adicionar barra de progresso
        for future in tqdm(concurrent.futures.as_completed(futures), total=num_paginas, desc="Progresso"):
            content = future.result()
            if content:
                page_data = process_page_content(content)
                all_data.extend(page_data)
                total_imoveis += len(page_data)
                if total_imoveis >= num_imoveis_desejados:
                    break

    # Limitar o número de imóveis desejados
    all_data = all_data[:num_imoveis_desejados]

    df_imovel = pd.DataFrame(all_data, columns=['Título', 'Subtítulo', 'Link', 'Preço', 'Metro Quadrado', 'Quarto', 'Vaga', 'Tipo'])

    # Separar 'Subtítulo' em 'Bairro' e 'Cidade'
    df_imovel[['Bairro', 'Cidade']] = df_imovel['Subtítulo'].str.split(',', expand=True)
    df_imovel['Bairro'] = df_imovel['Bairro'].str.strip()
    df_imovel['Cidade'] = df_imovel['Cidade'].str.strip()
    df_imovel.drop(columns=['Subtítulo'], inplace=True)

    # Converte as colunas para valores numéricos, preenchendo com NaN onde não for possível
    df_imovel['Preço'] = pd.to_numeric(df_imovel['Preço'], errors='coerce')
    df_imovel['Metro Quadrado'] = pd.to_numeric(df_imovel['Metro Quadrado'], errors='coerce')
    df_imovel['Quarto'] = pd.to_numeric(df_imovel['Quarto'], errors='coerce')
    df_imovel['Vaga'] = pd.to_numeric(df_imovel['Vaga'], errors='coerce')

    # Adicionar nova coluna 'M2' e calcular a divisão
    df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Metro Quadrado']

    # Remover linhas onde 'Preço' ou 'Metro Quadrado' são 0, nulos ou vazios
    df_imovel.dropna(subset=['Preço', 'Metro Quadrado'], inplace=True)
    df_imovel = df_imovel[(df_imovel['Preço'] != 0) & (df_imovel['Metro Quadrado'] != 0)]
    
    # Substituir os valores vazios por 0 nas colunas especificadas
    colunas_para_preencher = ["Preço", "Metro Quadrado", "Quarto", "Vaga", "M2"]
    df_imovel[colunas_para_preencher] = df_imovel[colunas_para_preencher].fillna(0)

    # Write DataFrame to Excel file
    df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\base_de_dados_excel\credito_real_data_base\credito_real_venda_07_2024.xlsx', index=False)

    fim = time.time()
    tempo_total_segundos = fim - inicio
    horas = int(tempo_total_segundos // 3600)
    tempo_total_segundos %= 3600
    minutos = int(tempo_total_segundos // 60)
    segundos = int(tempo_total_segundos % 60)

    logging.info(f'O script demorou {horas} horas, {minutos} minutos e {segundos} segundos para ser executado.')

if __name__ == '__main__':
    main()
