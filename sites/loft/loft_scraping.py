import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import logging
from tqdm import tqdm
from datetime import datetime
from random import randint
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = 'https://loft.com.br'
SEARCH_URL = BASE_URL + '/venda/imoveis/sp/sao-paulo?pagina={}'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

MAX_RETRIES = 3

# Função para limpar colunas numéricas
def clean_numeric_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """Remove non-numeric characters and converts columns to numeric."""
    for column in columns:
        df[column] = df[column].str.replace(r'\D', '', regex=True)
        df[column] = pd.to_numeric(df[column], errors='coerce')
    return df

# Função para extrair dados de uma página
def extract_data_from_page(page_url: str) -> List[Dict]:
    """Extracts property data from a given page URL."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(page_url, headers=HEADERS)
            response.raise_for_status()
            break
        except requests.RequestException as e:
            logging.error(f"Request failed (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(2)
    else:
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    properties = soup.find_all('a', class_='MuiButtonBase-root MuiCardActionArea-root jss319')
    data = []

    for prop in properties:
        try:
            link = BASE_URL + prop['href'] if prop.get('href') else None
            property_type = prop.find('span', id='property-type').text if prop.find('span', id='property-type') else None
            price = prop.find('div', class_='jss363').find('span').text if prop.find('div', class_='jss363') and prop.find('div', class_='jss363').find('span') else None
            address = prop.find('h2', class_='MuiTypography-root jss203 jss181 jss194 jss368 MuiTypography-body1 MuiTypography-noWrap').text if prop.find('h2', class_='MuiTypography-root jss203 jss181 jss194 jss368 MuiTypography-body1 MuiTypography-noWrap') else None
            
            area = None
            bedrooms = None
            parking_spaces = None

            details = prop.find_all('div', class_='jss369')

            if len(details) >= 3:
                area = details[0].find('span').text if details[0].find('span') else None
                bedrooms = details[1].find('span').text if details[1].find('span') else None
                parking_spaces = details[2].find('span').text if details[2].find('span') else None

            data.append({
                'Link': link,
                'Tipo do Imóvel': property_type,
                'Preço': price,
                'Endereço': address,
                'Área': area,
                'Quartos': bedrooms,
                'Vagas': parking_spaces
            })
        except AttributeError as e:
            logging.error(f"Error extracting property data: {e}")
            continue

    return data

# Função para limpar e formatar endereço
def clean_address(df: pd.DataFrame) -> pd.DataFrame:
    """Splits address into 'Rua' and 'Bairro'."""
    df[['Rua', 'Bairro']] = df['Endereço'].str.split(',', expand=True, n=1)
    return df

# Função principal de scraping com paralelização
def scrape_properties(num_pages: int, max_workers: int = 5) -> pd.DataFrame:
    """Scrapes property data from multiple pages using multithreading."""
    all_data = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(extract_data_from_page, SEARCH_URL.format(page)): page for page in range(1, num_pages + 1)}
        
        for future in tqdm(as_completed(future_to_url), total=num_pages, desc="Scraping pages"):
            try:
                data = future.result()
                all_data.extend(data)
            except Exception as e:
                logging.error(f"Error processing page: {e}")
    
    df = pd.DataFrame(all_data)

    # Limpar colunas numéricas
    numeric_columns = ['Preço', 'Área', 'Quartos', 'Vagas']
    df = clean_numeric_columns(df, numeric_columns)

    # Remover imóveis com preços inválidos
    df = df.dropna(subset=['Preço'])
    df = df[df['Preço'] > 0]

    # Dividir a coluna "Endereço" em "Rua" e "Bairro"
    df = clean_address(df)

    # Adicionar coluna "M2" (Preço/Área)
    df['M2'] = df['Preço'] / df['Área']

    return df

def main():
    """Main function to execute the scraping and save the results."""
    num_pages = 132  # Ajuste o número de páginas conforme necessário
    df = scrape_properties(num_pages, max_workers=10)

    timestamp = datetime.now().strftime('%Y%m%d')
    file_name = f'imoveis_loft_{timestamp}.xlsx'
    
    df.to_excel(file_name, index=False)
    logging.info(f'Dados extraídos e salvos em {file_name}')

if __name__ == "__main__":
    main()
