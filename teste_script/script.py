import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
import time
import logging
import concurrent.futures
from tqdm import tqdm

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Headers customizados
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Referer': 'https://www.imovelweb.com.br/',
}

def configure_session():
    """Configura a sessão de requests com headers customizados."""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session

def extract_page_data(session, page):
    """Extrai o conteúdo HTML de uma página específica."""
    url = f'https://www.creditoreal.com.br/vendas?page={page}'
    try:
        response = session.get(url)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f'Erro ao acessar a página {page}: {e}')
        return None

def parse_imovel(imovel):
    """Extrai informações de um imóvel específico a partir do HTML."""
    try:
        titulo = imovel.find('span', attrs={'class': 'sc-e9fa241f-1 fdybXW'}).text.strip()
        link = 'https://www.creditoreal.com.br' + imovel['href']
        subtitulo = imovel.find('span', attrs={'class': 'sc-e9fa241f-1 hqggtn'}).text.strip()
        tipo = imovel.find('span', attrs={'class': 'sc-e9fa241f-0 bTpAju imovel-type'}).text.strip()
        preco = re.sub(r'\D', '', imovel.find('p', attrs={'class': 'sc-e9fa241f-1 ericyj'}).text)

        metro_area = imovel.find('div', attrs={'class': 'sc-b308a2c-2 iYXIja'})
        if metro_area:
            metro_text = metro_area.find('p', attrs={'class': 'sc-e9fa241f-1 jUSYWw'}).text.strip()
            metro_value = float(re.search(r'(\d+)', metro_text).group(1))
            if 'hectares' in metro_text.lower():
                metro_value *= 10000
        else:
            metro_value = None

        quarto_vaga = metro_area.findAll('p', attrs={'class': 'sc-e9fa241f-1 jUSYWw'})
        quarto, vaga = None, None
        for item in quarto_vaga:
            text = item.text.lower()
            if 'quartos' in text:
                quarto = re.search(r'(\d+)', text).group(1)
            elif 'vaga' in text:
                vaga = re.search(r'(\d+)', text).group(1)

        return {
            'Título': titulo,
            'Subtítulo': subtitulo,
            'Link': link,
            'Preço': preco,
            'Metro Quadrado': metro_value,
            'Quarto': quarto,
            'Vaga': vaga,
            'Tipo': tipo
        }

    except AttributeError as e:
        logging.warning(f'Erro ao extrair dados do imóvel: {e}')
        return None

def process_page_content(content):
    """Processa o conteúdo HTML da página e extrai dados dos imóveis."""
    site = BeautifulSoup(content, 'html.parser')
    imoveis = site.findAll('a', attrs={'class': 'sc-613ef922-1 iJQgSL'})
    data = [parse_imovel(imovel) for imovel in imoveis]
    return [item for item in data if item]

def extract_additional_info(session, link):
    """Extrai informações adicionais de um imóvel a partir do link."""
    try:
        response = session.get(link)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        endereco = soup.find('span', attrs={'class': 'sc-e9fa241f-1 hqggtn'})
        descricao = soup.find('p', attrs={'class': 'sc-e9fa241f-1 fAJgAs'})

        endereco_texto = endereco.text.strip() if endereco else None
        descricao_texto = descricao.text.strip() if descricao else None

        banheiro, suite, mobilia = None, None, 0
        detalhes = soup.findAll('p', attrs={'class': 'sc-e9fa241f-1 jUSYWw'})
        for detalhe in detalhes:
            texto = detalhe.text.lower()
            if 'banheiro' in texto:
                banheiro = re.search(r'(\d+)', texto).group(1)
            elif 'suíte' in texto:
                suite = re.search(r'(\d+)', texto).group(1)
            elif 'mobilia' in texto:
                mobilia = 1 if 'sem' not in texto else 0

        div_amenidades = soup.find('div', attrs={'class': 'sc-b953b8ee-4 sFtII'})
        amenidades = [amenidade.text.strip() for amenidade in div_amenidades.findAll('div', attrs={'class': 'sc-c019b9bb-0 iZYuDq'})] if div_amenidades else []

        return {
            'Descrição': descricao_texto,
            'Endereço': endereco_texto,
            'Banheiro': banheiro,
            'Suíte': suite,
            'Mobilia': mobilia,
            'Amenidades': amenidades
        }
    except requests.exceptions.RequestException as e:
        logging.error(f'Erro ao acessar o link {link}: {e}')
        return None

def main():
    """Função principal que executa o scraping e processa os dados."""
    inicio = time.time()
    session = configure_session()
    all_data = []

    # Extrair dados das páginas
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(extract_page_data, session, page): page for page in range(1, 340)}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Processando páginas"):
            content = future.result()
            if content:
                all_data.extend(process_page_content(content))

    # Filtrando dados nulos
    all_data = [data for data in all_data if data]

    # Criação do DataFrame inicial
    df_imovel = pd.DataFrame(all_data)

    # Converte as colunas para valores numéricos, preenchendo com NaN onde não for possível
    df_imovel['Preço'] = pd.to_numeric(df_imovel['Preço'], errors='coerce')
    df_imovel['Metro Quadrado'] = pd.to_numeric(df_imovel['Metro Quadrado'], errors='coerce')
    df_imovel['Quarto'] = pd.to_numeric(df_imovel['Quarto'], errors='coerce')
    df_imovel['Vaga'] = pd.to_numeric(df_imovel['Vaga'], errors='coerce')

    # Adiciona nova coluna 'M2' e calcula a divisão
    df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Metro Quadrado']

    # Remover linhas onde 'Preço' ou 'Metro Quadrado' são 0, nulos ou vazios
    df_imovel.dropna(subset=['Preço', 'Metro Quadrado'], inplace=True)
    df_imovel = df_imovel[(df_imovel['Preço'] != 0) & (df_imovel['Metro Quadrado'] != 0)]
    
    # Substituir os valores vazios por 0 nas colunas especificadas
    colunas_para_preencher = ["Preço", "Metro Quadrado", "Quarto", "Vaga", "M2"]
    df_imovel[colunas_para_preencher] = df_imovel[colunas_para_preencher].fillna(0)

    # Extração de informações adicionais
    additional_data = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(extract_additional_info, session, link): link for link in df_imovel['Link']}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Processando links adicionais"):
            additional_info = future.result()
            if additional_info:
                additional_data.append(additional_info)

    additional_df = pd.DataFrame(additional_data)
    df_imovel = pd.concat([df_imovel.reset_index(drop=True), additional_df.reset_index(drop=True)], axis=1)

    # Expand amenities into separate columns
    all_amenities = set([amenidade for sublist in df_imovel['Amenidades'].dropna() for amenidade in sublist])
    for amenity in all_amenities:
        df_imovel[amenity] = df_imovel['Amenidades'].apply(lambda x: 1 if amenity in x else 0)
    df_imovel.drop(columns=['Amenidades'], inplace=True)

    # Reorder the columns
    column_order = ['Título', 'Subtítulo', 'Link', 'Preço', 'Metro Quadrado', 'Quarto', 'Vaga', 'Banheiro', 'Suíte', 'Mobilia', 'Tipo', 'Descrição', 'Endereço', 'M2'] + list(all_amenities)
    df_imovel = df_imovel[column_order]
    
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
