import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from multiprocessing import cpu_count
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
import numpy as np
from cachetools import cached, TTLCache

# Configurações de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Headers customizados
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Referer': 'https://www.franciosi.com.br/',
}

# Variável para definir o número de páginas a serem percorridas
NUM_PAGINAS = 400  # Altere este valor para o número de páginas desejado

# Cache de TTL para armazenar respostas HTTP (10 minutos)
cache = TTLCache(maxsize=1000, ttl=600)

def configurar_sessao():
    """Configura a sessão de requests com headers customizados."""
    session = requests.Session()
    session.headers.update(HEADERS)
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=200, pool_maxsize=200)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

@cached(cache)
def extrair_dados_pagina(sessao, pagina):
    """Extrai o conteúdo HTML de uma página específica."""
    url = f'https://www.franciosi.com.br/pesquisa-de-imoveis/?locacao_venda=V&id_cidade[]=26&finalidade=&dormitorio=&garagem=&vmi=&vma=&ordem=4&&pag={pagina}'
    try:
        response = sessao.get(url)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f'Erro ao acessar a página {pagina}: {e}')
        return None

def parsear_imovel(imovel_html):
    """Extrai informações de um imóvel específico a partir do HTML."""
    try:
        link_elem = imovel_html.find('a', class_='carousel-cell')
        link = 'https://www.franciosi.com.br/' + link_elem['href'] if link_elem else 'Link não disponível'

        preco_venda, preco_aluguel = '0', '0'
        card_valores = imovel_html.select('.card-valores div')
        for valor in card_valores:
            if 'V' in valor.text:
                preco_venda = valor.text.replace('R$', '').replace('V', '').strip()
            elif 'L' in valor.text:
                preco_aluguel = valor.text.replace('R$', '').replace('L', '').strip()

        endereco_elem = imovel_html.find('p', class_='card-bairro-cidade')
        endereco = endereco_elem.text.strip() if endereco_elem else 'Endereço não disponível'
        bairro, cidade, estado = (endereco.split(' - ') + [''] * 3)[:3]

        subtitulo_elem = imovel_html.find('p', class_='card-texto')
        subtitulo = subtitulo_elem.text.strip() if subtitulo_elem else 'Subtítulo não disponível'

        detalhes_elem = imovel_html.find('li', class_='list-group-item')
        if detalhes_elem:
            quartos = int(detalhes_elem.find('div', class_='dorm-ico').find_all('span')[1].text.strip()) if detalhes_elem.find('div', class_='dorm-ico') and detalhes_elem.find('div', class_='dorm-ico').find_all('span') else 0
            suites = int(detalhes_elem.find('div', class_='suites-ico').find_all('span')[1].text.strip()) if detalhes_elem.find('div', class_='suites-ico') and detalhes_elem.find('div', class_='suites-ico').find_all('span') else 0
            banheiros = int(detalhes_elem.find('div', class_='banh-ico').find_all('span')[1].text.strip()) if detalhes_elem.find('div', class_='banh-ico') and detalhes_elem.find('div', class_='banh-ico').find_all('span') else 0
            garagens = int(detalhes_elem.find('div', class_='gar-ico').find_all('span')[1].text.strip()) if detalhes_elem.find('div', class_='gar-ico') and detalhes_elem.find('div', class_='gar-ico').find_all('span') else 0
        else:
            quartos, suites, banheiros, garagens = 0, 0, 0, 0

        return {
            'Link': link,
            'Preço Venda': preco_venda,
            'Preço Aluguel': preco_aluguel,
            'Bairro': bairro,
            'Cidade': cidade,
            'Estado': estado,
            'Subtítulo': subtitulo,
            'Quarto': quartos,
            'Suíte': suites,
            'Banheiro': banheiros,
            'Garagem': garagens
        }

    except AttributeError as e:
        logging.warning(f'Erro ao extrair dados do imóvel: {e}')
        return None

def processar_conteudo_pagina(conteudo):
    """Processa o conteúdo HTML da página e extrai dados dos imóveis."""
    site = BeautifulSoup(conteudo, 'html.parser')
    imoveis = site.findAll('div', class_='card card-imo')
    data = [parsear_imovel(imovel) for imovel in tqdm(imoveis, desc="Processando imóveis")]
    return [item for item in data if item]

def limpar_valor(valor):
    """Remove caracteres indesejados de valores numéricos."""
    valor = re.sub(r'[^\d,]', '', valor)  # Remove tudo exceto dígitos e vírgulas
    valor = valor.replace('.', '').replace(',', '.')
    return float(valor) if valor else 0.0

def extrair_informacoes_adicionais(sessao, link):
    """Extrai informações adicionais de uma página específica do imóvel."""
    try:
        resposta = sessao.get(link)
        resposta.raise_for_status()
        soup = BeautifulSoup(resposta.content, 'html.parser')

        detalhes = {}
        for item in soup.select('.property-detail-item'):
            label = item.select_one('.property-detail-label').get_text(strip=True)
            valor = item.select_one('.property-detail-value').get_text(strip=True)
            detalhes[label] = limpar_valor(valor)

        area_terreno = float(detalhes.get('Área do terreno', '0').replace(' m²', ''))
        area_construida = float(detalhes.get('Área construída', '0').replace(' m²', ''))
        area_util = float(detalhes.get('Área útil', '0').replace(' m²', ''))

        amenidades = [a.get_text(strip=True) for a in soup.select('.amenities-item')]

        return {
            'Link': link,
            'Área Terreno': area_terreno,
            'Área Construída': area_construida,
            'Área Útil': area_util,
            'Amenidades': amenidades
        }
    except Exception as e:
        logging.error(f"Erro ao extrair dados do link {link}: {e}")
        return None

def tratar_dados(df):
    """Trata os dados do DataFrame, convertendo tipos e lidando com valores ausentes."""
    try:
        df['Preço Venda'] = df['Preço Venda'].apply(limpar_valor).astype(float).fillna(0)
        df['Preço Aluguel'] = df['Preço Aluguel'].apply(limpar_valor).astype(float).fillna(0)
        df['Quarto'] = pd.to_numeric(df['Quarto'], errors='coerce').fillna(0).astype(int)
        df['Suíte'] = pd.to_numeric(df['Suíte'], errors='coerce').fillna(0).astype(int)
        df['Banheiro'] = pd.to_numeric(df['Banheiro'], errors='coerce').fillna(0).astype(int)
        df['Garagem'] = pd.to_numeric(df['Garagem'], errors='coerce').fillna(0).astype(int)
        df['Área Terreno'] = pd.to_numeric(df['Área Terreno'], errors='coerce').fillna(0).astype(float)
        df['Área Construída'] = pd.to_numeric(df['Área Construída'], errors='coerce').fillna(0).astype(float)
        df['Área Útil'] = pd.to_numeric(df['Área Útil'], errors='coerce').fillna(0).astype(float)

        df['M2 Aluguel'] = df.apply(lambda x: x['Preço Aluguel'] / x['Área Terreno'] if x['Área Terreno'] else 0, axis=1)
        df['M2 Venda'] = df.apply(lambda x: x['Preço Venda'] / x['Área Terreno'] if x['Área Terreno'] else 0, axis=1)

    except Exception as e:
        logging.error(f"Erro ao tratar dados: {e}")
    return df

def coletar_dados_imoveis(sessao):
    """Coleta dados de imóveis de múltiplas páginas e retorna um DataFrame."""
    resultados = []
    with ThreadPoolExecutor(max_workers=cpu_count() * 2) as executor:
        futuros = [executor.submit(extrair_dados_pagina, sessao, pagina) for pagina in range(1, NUM_PAGINAS + 1)]
        for futuro in as_completed(futuros):
            conteudo = futuro.result()
            if conteudo:
                resultados.extend(processar_conteudo_pagina(conteudo))
    
    df = pd.DataFrame(resultados)
    df = tratar_dados(df)

    links = df['Link'].tolist()
    resultados_detalhados = []
    with ThreadPoolExecutor(max_workers=cpu_count() * 2) as executor:
        futuros = [executor.submit(extrair_informacoes_adicionais, sessao, link) for link in links]
        for futuro in as_completed(futuros):
            resultado = futuro.result()
            if resultado:
                resultados_detalhados.append(resultado)

    df_detalhado = pd.DataFrame(resultados_detalhados)
    df = df.merge(df_detalhado, on='Link', how='left')

    df = tratar_dados(df)
    return df

def main():
    sessao = configurar_sessao()
    imoveis_data = coletar_dados_imoveis(sessao)
    imoveis_data.to_excel('dados_imoveis.xlsx', index=False)
    logging.info("Dados salvos em dados_imoveis.csv")

if __name__ == "__main__":
    main()
