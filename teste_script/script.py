import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pandas as pd
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from multiprocessing import cpu_count
from cachetools import cached, TTLCache
from dataclasses import dataclass, asdict
from time import time

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='scraping.log', filemode='a')

# Headers customizados
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Referer': 'https://www.creditoreal.com.br/',
}

# Variável para definir o número de páginas a serem percorridas
NUM_PAGINAS = 1000  # Altere este valor para o número de páginas desejado

# Cache de TTL para armazenar respostas HTTP (10 minutos)
cache = TTLCache(maxsize=1000, ttl=600)

@dataclass
class Imovel:
    """Classe que representa um imóvel."""
    Titulo: str
    Subtitulo: str
    Link: str
    Preco: str
    MetroQuadrado: float
    Quarto: int
    Vaga: int
    Tipo: str
    Descricao: str = ''
    Endereco: str = ''
    Banheiro: int = 0
    Suite: int = 0
    Mobilia: int = 0
    Amenidades: list = None

    def to_dict(self):
        return asdict(self)

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
    url = f'https://www.creditoreal.com.br/vendas?page={pagina}'
    try:
        response = sessao.get(url, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f'Erro ao acessar a página {pagina}: {e}')
        return None

def parsear_imovel(imovel_html):
    """Extrai informações de um imóvel específico a partir do HTML."""
    try:
        titulo_elem = imovel_html.find('span', class_='sc-e9fa241f-1 fdybXW')
        titulo = titulo_elem.text.strip() if titulo_elem else 'Título não disponível'

        link = 'https://www.creditoreal.com.br' + imovel_html['href'] if imovel_html.get('href') else 'Link não disponível'

        subtitulo_elem = imovel_html.find('span', class_='sc-e9fa241f-1 hqggtn')
        subtitulo = subtitulo_elem.text.strip() if subtitulo_elem else 'Subtítulo não disponível'

        tipo_elem = imovel_html.find('span', class_='sc-e9fa241f-0 bTpAju imovel-type')
        tipo = tipo_elem.text.strip() if tipo_elem else 'Tipo não disponível'

        preco_elem = imovel_html.find('p', class_='sc-e9fa241f-1 ericyj')
        preco = re.sub(r'\D', '', preco_elem.text) if preco_elem and preco_elem.text else '0'

        metro_area = imovel_html.find('div', class_='sc-b308a2c-2 iYXIja')
        metro_value = 0
        if metro_area:
            metro_text_elem = metro_area.find('p', class_='sc-e9fa241f-1 jUSYWw')
            metro_text = metro_text_elem.text.strip() if metro_text_elem else ''
            if re.search(r'(\d+)', metro_text):
                metro_value = float(re.search(r'(\d+)', metro_text).group(1))
                if 'hectares' in metro_text.lower():
                    metro_value *= 10000

        quarto_vaga = metro_area.findAll('p', class_='sc-e9fa241f-1 jUSYWw') if metro_area else []
        quarto, vaga = 0, 0
        for item in quarto_vaga:
            text = item.text.lower()
            if 'quartos' in text:
                quarto = int(re.search(r'(\d+)', text).group(1)) if re.search(r'(\d+)', text) else 0
            elif 'vaga' in text:
                vaga = int(re.search(r'(\d+)', text).group(1)) if re.search(r'(\d+)', text) else 0

        return Imovel(
            Titulo=titulo,
            Subtitulo=subtitulo,
            Link=link,
            Preco=preco,
            MetroQuadrado=metro_value,
            Quarto=quarto,
            Vaga=vaga,
            Tipo=tipo
        )
    except AttributeError as e:
        logging.warning(f'Erro ao extrair dados do imóvel: {e}')
        return None

def processar_conteudo_pagina(conteudo):
    """Processa o conteúdo HTML da página e extrai dados dos imóveis."""
    site = BeautifulSoup(conteudo, 'lxml')
    imoveis = site.findAll('a', class_='sc-613ef922-1 iJQgSL')
    data = [parsear_imovel(imovel) for imovel in tqdm(imoveis, desc="Processando imóveis")]
    return [item for item in data if item is not None]

@cached(cache)
def extrair_informacoes_adicionais(sessao, link):
    """Extrai informações adicionais de um imóvel a partir de uma URL."""
    try:
        response = sessao.get(link, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')

        endereco_elem = soup.find('span', class_='sc-e9fa241f-1 hqggtn')
        endereco = endereco_elem.text.strip() if endereco_elem else 'Endereço não disponível'

        descricao_elem = soup.find('p', class_='sc-e9fa241f-1 fAJgAs')
        descricao = descricao_elem.text.strip() if descricao_elem else 'Descrição não disponível'

        banheiro, suite, mobilia = 0, 0, 0
        detalhes = soup.findAll('p', class_='sc-e9fa241f-1 jUSYWw')
        for detalhe in detalhes:
            texto = detalhe.text.lower()
            if 'banheiro' in texto:
                banheiro = int(re.search(r'(\d+)', texto).group(1)) if re.search(r'(\d+)', texto) else 0
            elif 'suite' in texto:
                suite = int(re.search(r'(\d+)', texto).group(1)) if re.search(r'(\d+)', texto) else 0
            elif 'mobilia' in texto:
                mobilia = 1 if 'com' in texto else 0

        div_amenidades = soup.find('div', class_='sc-b953b8ee-4 sFtII')
        amenidades = [amenidade.text.strip() for amenidade in div_amenidades.findAll('div', class_='sc-c019b9bb-0 iZYuDq')] if div_amenidades else []

        return {
            'Descricao': descricao,
            'Endereco': endereco,
            'Banheiro': banheiro,
            'Suite': suite,
            'Mobilia': mobilia,
            'Amenidades': amenidades
        }
    except Exception as e:
        logging.error(f'Erro ao extrair dados do link {link}: {e}')
        return None

def tratar_dados(df):
    """Trata os dados do DataFrame."""
    try:
        # Remover caracteres não numéricos e converter colunas para numéricas
        df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')
        df['MetroQuadrado'] = pd.to_numeric(df['MetroQuadrado'], errors='coerce')
        df['Quarto'] = pd.to_numeric(df['Quarto'], errors='coerce').fillna(0).astype(int)
        df['Vaga'] = pd.to_numeric(df['Vaga'], errors='coerce').fillna(0).astype(int)
        df['Banheiro'] = pd.to_numeric(df['Banheiro'], errors='coerce').fillna(0).astype(int)
        df['Suite'] = pd.to_numeric(df['Suite'], errors='coerce').fillna(0).astype(int)
        df['Mobilia'] = pd.to_numeric(df['Mobilia'], errors='coerce').fillna(0).astype(int)

        # Excluir imóveis com preço ou metro quadrado inválidos
        df = df[(df['Preco'] > 0) & (df['MetroQuadrado'] > 0)]

        # Separar subtítulo em bairro e cidade
        df[['Bairro', 'Cidade']] = df['Subtitulo'].str.split(', ', expand=True)
        df.drop(columns=['Subtitulo'], inplace=True)

        # Tratar as amenidades
        todas_amenidades = set()
        for amenidades in df['Amenidades']:
            if isinstance(amenidades, list):
                todas_amenidades.update(amenidades)

        for amenidade in todas_amenidades:
            df[amenidade] = df['Amenidades'].apply(lambda x: 1 if isinstance(x, list) and amenidade in x else 0)

        df.drop(columns=['Amenidades'], inplace=True)

        # Rearranjar colunas
        colunas_ordenadas = [
            'Titulo', 'Link', 'Preco', 'MetroQuadrado', 'Quarto', 'Banheiro', 'Suite',
            'Vaga', 'Mobilia', 'Tipo', 'Bairro', 'Cidade', 'Descricao', 'Endereco'
        ]
        colunas_ordenadas += list(todas_amenidades)
        df = df[colunas_ordenadas]

        df.replace('', pd.NA, inplace=True)
    except Exception as e:
        logging.error(f'Erro ao tratar dados: {e}')

    return df

def main():
    """Função principal que executa o scraping e processa os dados."""
    inicio = time()

    with configurar_sessao() as sessao:
        todos_dados = []

        # Extrair dados das páginas
        with ThreadPoolExecutor(max_workers=cpu_count() * 2) as executor:
            future_to_page = {executor.submit(extrair_dados_pagina, sessao, p): p for p in range(1, NUM_PAGINAS + 1)}

            for future in tqdm(as_completed(future_to_page), total=NUM_PAGINAS, desc="Baixando páginas"):
                pagina = future_to_page[future]
                try:
                    conteudo = future.result()
                    if conteudo:
                        todos_dados.extend(processar_conteudo_pagina(conteudo))
                except Exception as e:
                    logging.error(f'Erro ao processar a página {pagina}: {e}')

        # Filtrando dados nulos
        todos_dados = [dado for dado in todos_dados if dado is not None]

        # Baixar HTML adicional e extrair informações adicionais
        with ThreadPoolExecutor(max_workers=cpu_count() * 2) as executor:
            future_to_link = {executor.submit(extrair_informacoes_adicionais, sessao, dado.Link): dado for dado in todos_dados}

            for future in tqdm(as_completed(future_to_link), total=len(todos_dados), desc="Extraindo informações adicionais"):
                dado = future_to_link[future]
                try:
                    info_adicional = future.result()
                    if info_adicional:
                        for key, value in info_adicional.items():
                            setattr(dado, key, value)
                except Exception as e:
                    logging.error(f'Erro ao processar informações adicionais do link {dado.Link}: {e}')

        # Criando DataFrame e tratando os dados
        df = pd.DataFrame([dado.to_dict() for dado in todos_dados])
        df.replace('', pd.NA, inplace=True)
        df = tratar_dados(df)

        # Salvando em arquivo Excel
        try:
            df.to_excel('dados_imoveis_tratados.xlsx', index=False)
        except Exception as e:
            logging.error(f'Erro ao salvar arquivo Excel: {e}')

        fim = time()
        logging.info(f'Tempo total: {(fim - inicio) / 60:.2f} minutos')

if __name__ == "__main__":
    main()
