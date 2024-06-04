import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from distrito_federal_setor import setores

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração de cabeçalhos
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
}

# URL base e número de páginas
BASE_URL = 'https://www.dfimoveis.com.br/aluguel/df/todos/imoveis?pagina='
NUM_PAGES = 244

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
    titulo = imovel.find('h2', attrs={'class': 'new-title'})
    link = 'https://www.dfimoveis.com.br' + imovel['href']
    subtitulo = imovel.find('h3', attrs={'class': 'new-simple'})
    imobiliaria_area = imovel.find('div', attrs={'class': 'new-anunciante'})
    imobiliaria = imobiliaria_area.find('img', alt=True)['alt']
    preco_area = imovel.find('div', attrs={'class': 'new-price'})
    preco = preco_area.find('h4')
    metro = imovel.find('li', attrs={'class': 'm-area'})
    
    quarto_suite_vaga = imovel.find('ul', attrs={'class': 'new-details-ul'})
    quarto = suite = vaga = None
    if quarto_suite_vaga:
        lista = quarto_suite_vaga.findAll('li')
        for item in lista:
            if 'quartos' in item.text.lower():
                quarto = re.search(r'(\d+)', item.text).group(1)
            elif 'suítes' in item.text.lower():
                suite = re.search(r'(\d+)', item.text).group(1)
            elif 'vagas' in item.text.lower():
                vaga = re.search(r'(\d+)', item.text).group(1)
    
    if titulo and subtitulo and preco and metro:
        if 'a' not in metro.text and preco.text.strip() != "R$ Sob Consulta":
            metro_value = re.search(r'\d+', metro.text.replace('m²', '').strip())
            return [
                titulo.text.strip(), subtitulo.text.strip(), link, 
                re.sub(r'\D', '', preco.text), 
                metro_value.group() if metro_value else None, 
                quarto or '0', suite or '0', vaga or '0', imobiliaria
            ]
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
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_page = {executor.submit(fetch_page, session, page): page for page in range(1, NUM_PAGES+1)}
            
            for future in as_completed(future_to_page):
                content = future.result()
                if content:
                    lista_de_imoveis.extend(process_page_content(content))
    
    df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo', 'Link', 'Preço', 'Área', 'Quarto', 'Suite', 'Vaga', 'Imobiliária'])
    
    # Remover duplicatas com base na coluna 'Link'
    df_imovel.drop_duplicates(subset='Link', inplace=True)
    
    # Converte as colunas para valores numéricos, preenchendo com NaN onde não for possível
    df_imovel['Preço'] = pd.to_numeric(df_imovel['Preço'], errors='coerce')
    df_imovel['Área'] = pd.to_numeric(df_imovel['Área'], errors='coerce')
    df_imovel['Quarto'] = pd.to_numeric(df_imovel['Quarto'], errors='coerce')
    df_imovel['Suite'] = pd.to_numeric(df_imovel['Suite'], errors='coerce')
    df_imovel['Vaga'] = pd.to_numeric(df_imovel['Vaga'], errors='coerce')

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
    df_imovel['Tipo'] = df_imovel['Link'].apply(extrair_tipo)

    # Salvar DataFrame em um arquivo Excel
    output_path = r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\base_de_dados_excel\df_imoveis_data_base\df_imoveis_df_aluguel_06_2024.xlsx'
    df_imovel.to_excel(output_path, index=False)

    logging.info(f'Dados salvos em {output_path}')

if __name__ == '__main__':
    main()
