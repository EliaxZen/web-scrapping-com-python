import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import logging
import concurrent.futures
from tqdm import tqdm

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Headers customizados
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, como Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Referer': 'https://www.auxiliadorapredial.com.br',
}

def configure_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    return session

def extract_page_data(session, page):
    url = f'https://www.auxiliadorapredial.com.br/comprar/residencial/rs+porto-alegre?page={page}'
    try:
        response = session.get(url)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f'Erro ao acessar a página {page}: {e}')
        return None

def parse_imovel(imovel):
    try:
        titulo = imovel.find('div', class_='RuaContainer')
        if titulo:
            titulo = titulo.find('span', class_='RuaSpan').text.strip()
        else:
            titulo = 'N/A'

        subtitulo = imovel.find('div', class_='Location')
        if subtitulo:
            subtitulo = subtitulo.find('span').text.strip()
        else:
            subtitulo = 'N/A'

        preco = imovel.find('div', class_='total')
        if preco:
            preco = preco.find('div', class_='oldValue')
            if preco:
                preco = preco.find('span', class_='fontSize16 bold green').text.strip()
                preco_value = re.sub(r'\D', '', preco)
            else:
                preco_value = 0
        else:
            preco_value = 0

        details = imovel.find('div', class_='Details')
        if details:
            metros = details.find_all('div')
            metro = int(re.sub(r'\D', '', metros[0].find('span').text.strip())) if len(metros) > 0 else 0
            quartos = int(metros[1].find('span').text.strip()) if len(metros) > 1 else 0
            vagas = int(metros[2].find('span').text.strip()) if len(metros) > 2 else 0
            banheiros = int(metros[3].find('span').text.strip()) if len(metros) > 3 else 0
        else:
            metro = quartos = vagas = banheiros = 0

        # Atualizar a extração do link
        link_tag = imovel.find('a', href=True)
        if link_tag:
            link = 'https://www.auxiliadorapredial.com.br' + link_tag['href']
        else:
            # Verificar se o link está em outro lugar, como dentro do swiper
            swiper = imovel.find('div', class_='swiper')
            if swiper:
                link_tag = swiper.find('a', href=True)
                if link_tag:
                    link = 'https://www.auxiliadorapredial.com.br' + link_tag['href']
                else:
                    link = 'N/A'
            else:
                link = 'N/A'

        return [titulo, subtitulo, link, preco_value, metro, quartos, vagas, banheiros]
    except Exception as e:
        logging.error(f'Erro ao processar o imóvel: {e}')
        return None

def process_page_content(content):
    site = BeautifulSoup(content, 'html.parser')
    imoveis = site.find_all('div', class_='content')
    data = [parse_imovel(imovel) for imovel in imoveis]
    return [item for item in data if item]

def main():
    inicio = time.time()
    session = configure_session()
    all_data = []

    total_pages = 51

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(extract_page_data, session, page): page for page in range(1, total_pages + 1)}
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=total_pages, desc="Processando páginas"):
            content = future.result()
            if content:
                all_data.extend(process_page_content(content))

    df_imovel = pd.DataFrame(all_data, columns=['Título', 'Subtítulo', 'Link', 'Preço', 'Metro Quadrado', 'Quartos', 'Vagas', 'Banheiros'])

    # Converte as colunas para valores numéricos, preenchendo com NaN onde não for possível
    df_imovel['Preço'] = pd.to_numeric(df_imovel['Preço'], errors='coerce')
    df_imovel['Metro Quadrado'] = pd.to_numeric(df_imovel['Metro Quadrado'], errors='coerce')
    df_imovel['Quartos'] = pd.to_numeric(df_imovel['Quartos'], errors='coerce')
    df_imovel['Vagas'] = pd.to_numeric(df_imovel['Vagas'], errors='coerce')
    df_imovel['Banheiros'] = pd.to_numeric(df_imovel['Banheiros'], errors='coerce')

    # Add new column 'M2' and calculate the division
    df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Metro Quadrado']

    # Remover linhas onde 'Preço' ou 'Metro Quadrado' são 0, nulos ou vazios
    df_imovel.dropna(subset=['Preço', 'Metro Quadrado'], inplace=True)
    df_imovel = df_imovel[(df_imovel['Preço'] != 0) & (df_imovel['Metro Quadrado'] != 0)]
    
    # Substituir os valores vazios por 0 nas colunas especificadas
    colunas_para_preencher = ["Preço", "Metro Quadrado", "Quartos", "Vagas", "Banheiros", "M2"]
    df_imovel[colunas_para_preencher] = df_imovel[colunas_para_preencher].fillna(0)

    # Write DataFrame to Excel file
    df_imovel.to_excel(r'auxiliadora_predial_porto_alegre_aluguel_06_2024_scrapping_normal.xlsx', index=False)

    fim = time.time()
    tempo_total_segundos = fim - inicio
    horas = int(tempo_total_segundos // 3600)
    tempo_total_segundos %= 3600
    minutos = int(tempo_total_segundos // 60)
    segundos = int(tempo_total_segundos % 60)

    logging.info(f'O script demorou {horas} horas, {minutos} minutos e {segundos} segundos para ser executado.')

if __name__ == '__main__':
    main()
