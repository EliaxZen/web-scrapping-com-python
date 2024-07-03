import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from distrito_federal_setor import setores
from tqdm import tqdm

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração de cabeçalhos
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
}

# URL base e número de páginas
BASE_URL = 'https://www.62imoveis.com.br/aluguel/go/todos/imoveis?pagina='
NUM_PAGES = 100

def fetch_page(session, page):
    try:
        url = f'{BASE_URL}{page}'
        response = session.get(url)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f'Erro ao acessar a página {page}: {e}')
        return None

def parse_imovel(imovel):
    try:
        titulo = imovel.find('h2', attrs={'class': 'new-title'}).text.strip()
        link = 'https://www.dfimoveis.com.br' + imovel['href']
        subtitulo = imovel.find('h3', attrs={'class': 'new-simple'}).text.strip()
        imobiliaria = imovel.find('div', attrs={'class': 'new-anunciante'}).find('img', alt=True)['alt']
        preco = re.sub(r'\D', '', imovel.find('div', attrs={'class': 'new-price'}).find('h4').text.strip())

        metro_text = imovel.find('li', attrs={'class': 'm-area'}).text.replace('m²', '').strip()
        metro_match = re.search(r'\d+', metro_text)
        metro_value = metro_match.group() if metro_match else None

        quarto_suite_vaga = imovel.find('ul', attrs={'class': 'new-details-ul'})
        quarto = suite = vaga = '0'
        if quarto_suite_vaga:
            lista = quarto_suite_vaga.findAll('li')
            for item in lista:
                text = item.text.lower()
                if 'quartos' in text:
                    quarto_match = re.search(r'(\d+)', text)
                    quarto = quarto_match.group(1) if quarto_match else '0'
                elif 'suítes' in text:
                    suite_match = re.search(r'(\d+)', text)
                    suite = suite_match.group(1) if suite_match else '0'
                elif 'vagas' in text:
                    vaga_match = re.search(r'(\d+)', text)
                    vaga = vaga_match.group(1) if vaga_match else '0'

        return [titulo, subtitulo, link, preco, metro_value, quarto, suite, vaga, imobiliaria]
    except Exception as e:
        logging.error(f'Erro ao parsear o imóvel: {e}')
        return None

def process_page_content(content):
    site = BeautifulSoup(content, 'html.parser')
    imoveis = site.findAll('a', attrs={'class': 'new-card'})
    data = [parse_imovel(imovel) for imovel in imoveis if parse_imovel(imovel)]
    return data

def main():
    lista_de_imoveis = []
    
    with requests.Session() as session:
        session.headers.update(HEADERS)
        
        with ThreadPoolExecutor(max_workers=20) as executor:  # Increased number of workers
            futures = [executor.submit(fetch_page, session, page) for page in range(1, NUM_PAGES + 1)]
            
            for future in tqdm(as_completed(futures), total=len(futures), desc="Processando páginas"):
                content = future.result()
                if content:
                    lista_de_imoveis.extend(process_page_content(content))
    
    df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo', 'Link', 'Preço', 'Área', 'Quarto', 'Suite', 'Vaga', 'Imobiliária'])
    
    # Remover duplicatas com base na coluna 'Link'
    df_imovel.drop_duplicates(subset='Link', inplace=True)
    
    # Converte as colunas para valores numéricos, preenchendo com NaN onde não for possível
    df_imovel[['Preço', 'Área', 'Quarto', 'Suite', 'Vaga']] = df_imovel[['Preço', 'Área', 'Quarto', 'Suite', 'Vaga']].apply(pd.to_numeric, errors='coerce')

    # Adiciona a coluna 'M2' e calcula a divisão
    df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Área']
    
    # Remove linhas onde 'Preço' ou 'Área' são 0, nulos ou vazios
    df_imovel.dropna(subset=['Preço', 'Área'], inplace=True)
    df_imovel = df_imovel[(df_imovel['Preço'] != 0) & (df_imovel['Área'] != 0)]

    # Função para extrair o setor da string de título
    def extrair_setor(titulo):
        palavras = titulo.split()
        palavras_upper = [palavra.upper() for palavra in palavras]
        for palavra in palavras_upper:
            if palavra in setores:
                return palavra
        return 'OUTRO'

    # Aplicar a função para extrair o setor e criar a nova coluna 'Setor'
    df_imovel['Setor'] = df_imovel['Título'].apply(extrair_setor)

    # Função para extrair o tipo do imóvel do link
    def extrair_tipo(link):
        tipos = {
            "apartamento": "Apartamento",
            "casa-condominio": "Casa Condomínio",
            "casa": "Casa",
            "galpo": "Galpão",
            "garagem": "Garagem",
            "hotel-flat": "Flat",
            "flat": "Flat",
            "kitnet": "Kitnet",
            "loja": "Loja",
            "loteamento": "Loteamento",
            "lote-terreno": "Lote Terreno",
            "ponto-comercial": "Ponto Comercial",
            "prdio": "Prédio",
            "predio": "Prédio",
            "sala": "Sala",
            "rural": "Zona Rural",
            "lancamento": "Lançamento",
        }
        for key, value in tipos.items():
            if key in link:
                return value
        return "OUTROS"

    # Adicionar uma coluna 'Tipo do Imóvel' ao DataFrame e preenchê-la com os tipos extraídos dos links
    df_imovel['Tipo'] = df_imovel['Link'].apply(extrair_tipo)

    # Salvar DataFrame em um arquivo Excel
    output_path = r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\base_de_dados_excel\62_imoveis_data_base\df_imoveis_GO_aluguel_07_2024.xlsx'
    df_imovel.to_excel(output_path, index=False)

    logging.info(f'Dados salvos em {output_path}')

if __name__ == '__main__':
    main()
