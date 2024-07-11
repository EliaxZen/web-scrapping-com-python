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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Referer': 'https://www.lelloimoveis.com.br',
}

# Configuração da sessão
def configure_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    return session

# Extração dos dados da página
def extract_page_data(session, url):
    try:
        response = session.get(url)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f'Erro ao acessar a URL {url}: {e}')
        return None

# Parser do imóvel
def parse_imovel(imovel):
    try:
        titulo_tag = imovel.find('h3', class_='font-weight-bold f-3 text-truncate text-neutral mb-0 f-2')
        titulo = titulo_tag.text.strip() if titulo_tag else None

        link_tag = imovel.find('a', class_='d-flex flex-column justify-content-between h-100')
        link = 'https://www.lelloimoveis.com.br' + link_tag['href'] if link_tag else None

        subtitulo_tag = imovel.find('span', class_='card-text-neighborhood f-1 text-truncate')
        subtitulo = subtitulo_tag.text.strip() if subtitulo_tag else None

        # Dividindo Subtítulo em Bairro e Cidade
        bairro, cidade = subtitulo.split(', ') if subtitulo and ', ' in subtitulo else (subtitulo, None)

        tipo_tag = imovel.find('div', class_='mb-2 card-title h5')
        tipo = tipo_tag.h2.text.strip() if tipo_tag else None

        preco_condominio_tag = imovel.find('div', class_='totalItemstyle__TotalItem-sc-t6cs2k-0 cyBCVE d-flex flex-column justify-content-between w-100 text-neutral-darkest realtyItemstyle__TotalItem-sc-dxx1wg-1 fYHxEW')
        preco = None
        condominio = None
        if preco_condominio_tag:
            preco = re.sub(r'\D', '', preco_condominio_tag.find_all('p')[0].text)
            condominio_text = preco_condominio_tag.find_all('p')[1].text if len(preco_condominio_tag.find_all('p')) > 1 else None
            condominio = re.sub(r'\D', '', condominio_text) if condominio_text else '0'

        area_tag = imovel.find('meta', itemprop='value')
        area = area_tag['content'] if area_tag else None

        quarto_tag = imovel.find('meta', itemprop='numberOfBedrooms')
        quarto = quarto_tag['content'] if quarto_tag else None

        banheiro_tag = imovel.find('meta', itemprop='numberOfBathroomsTotal')
        banheiro = banheiro_tag['content'] if banheiro_tag else None

        vaga_tag = imovel.find('span', attrs={'data-testid': 'realty-parking-lot-quantity'})
        vaga = None
        if vaga_tag:
            vaga_text = vaga_tag.text.strip()
            vaga = re.search(r'\d+', vaga_text).group(0) if vaga_text else None

        logging.debug(f'Título: {titulo}, Bairro: {bairro}, Cidade: {cidade}, Link: {link}, Preço: {preco}, Condomínio: {condominio}, Área: {area}, Quarto: {quarto}, Banheiro: {banheiro}, Vaga: {vaga}, Tipo: {tipo}')

        if titulo and bairro and cidade and preco and area:
            preco_value = float(preco)
            area_value = float(area)
            return [titulo, bairro, cidade, link, preco_value, condominio, area_value, quarto, banheiro, vaga, tipo]
    except Exception as e:
        logging.error(f'Erro ao parsear imóvel: {e}')
    return None

# Processamento do conteúdo da página
def process_page_content(content):
    site = BeautifulSoup(content, 'html.parser')
    imoveis = site.findAll('article', {'data-testid': 'realty-card'})
    data = [parse_imovel(imovel) for imovel in imoveis]
    return [item for item in data if item]

def main():
    inicio = time.time()
    session = configure_session()
    all_data = []

    # URLs para os imóveis comerciais e residenciais
    urls = [
        ('https://www.lelloimoveis.com.br/venda/comercial/{}-pagina/', 189),
        ('https://www.lelloimoveis.com.br/venda/residencial/{}-pagina/', 813)
    ]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Lista para armazenar futuros
        futures = []
        
        # Adiciona todas as combinações de URLs e páginas à lista de futuros
        for url_template, num_pages in urls:
            for page in range(1, num_pages + 1):
                url = url_template.format(page)
                futures.append(executor.submit(extract_page_data, session, url))
        
        # Processa os resultados com uma barra de progresso
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Processando páginas"):
            content = future.result()
            if content:
                all_data.extend(process_page_content(content))

    df_imovel = pd.DataFrame(all_data, columns=['Título', 'Bairro', 'Cidade', 'Link', 'Preço', 'Condomínio', 'Área', 'Quarto', 'Banheiro', 'Vaga', 'Tipo'])

    # Converte as colunas para valores numéricos, preenchendo com NaN onde não for possível
    df_imovel['Preço'] = pd.to_numeric(df_imovel['Preço'], errors='coerce')
    df_imovel['Condomínio'] = pd.to_numeric(df_imovel['Condomínio'], errors='coerce')
    df_imovel['Área'] = pd.to_numeric(df_imovel['Área'], errors='coerce')
    df_imovel['Quarto'] = pd.to_numeric(df_imovel['Quarto'], errors='coerce')
    df_imovel['Banheiro'] = pd.to_numeric(df_imovel['Banheiro'], errors='coerce')
    df_imovel['Vaga'] = pd.to_numeric(df_imovel['Vaga'], errors='coerce')

    # Adiciona nova coluna 'M2' e calcula a divisão
    df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Área']

    # Remove linhas onde 'Preço' ou 'Área' são 0, nulos ou vazios
    df_imovel.dropna(subset=['Preço', 'Área'], inplace=True)
    df_imovel = df_imovel[(df_imovel['Preço'] != 0) & (df_imovel['Área'] != 0)]
    
    # Substitui os valores vazios por 0 nas colunas especificadas
    colunas_para_preencher = ["Preço", "Condomínio", "Área", "Quarto", "Banheiro", "Vaga", "M2"]
    df_imovel[colunas_para_preencher] = df_imovel[colunas_para_preencher].fillna(0)

    # Escreve o DataFrame para um arquivo Excel
    df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\base_de_dados_excel\lello_data_base\lello_venda_07_2024.xlsx', index=False)

    fim = time.time()
    tempo_total_segundos = fim - inicio
    horas = int(tempo_total_segundos // 3600)
    tempo_total_segundos %= 3600
    minutos = int(tempo_total_segundos // 60)
    segundos = int(tempo_total_segundos % 60)

    logging.info(f'O script demorou {horas} horas, {minutos} minutos e {segundos} segundos para ser executado.')

if __name__ == '__main__':
    main()
