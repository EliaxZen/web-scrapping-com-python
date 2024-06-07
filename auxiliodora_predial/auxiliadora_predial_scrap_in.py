import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import logging
import concurrent.futures
from tqdm import tqdm
from pathlib import Path
import os
import tempfile

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Headers customizados
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Referer': 'https://www.auxiliadorapredial.com.br/',
}

def configurar_sessao():
    """Configura a sessão de requests com headers customizados."""
    session = requests.Session()
    session.headers.update(HEADERS)
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=100, pool_maxsize=100)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def extrair_dados_pagina(sessao, pagina):
    """Extrai o conteúdo HTML de uma página específica."""
    url = f'https://www.auxiliadorapredial.com.br/comprar/residencial/rs+porto-alegre?page={pagina}'
    try:
        response = sessao.get(url)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f'Erro ao acessar a página {pagina}: {e}')
        return None

def parsear_imovel(imovel):
    """Extrai informações de um imóvel específico a partir do HTML."""
    try:
        # Link do imóvel
        link_tag = imovel.find('a', href=True)
        link = 'https://www.auxiliadorapredial.com.br' + link_tag['href'] if link_tag else None

        # Preço
        preco_tag = imovel.find('div', class_='oldValue')
        preco = re.sub(r'\D', '', preco_tag.text) if preco_tag else None

        # Título e Subtítulo
        titulo_tag = imovel.find('div', class_='RuaContainer')
        titulo = titulo_tag.text.strip() if titulo_tag else None

        subtitulo_tag = imovel.find('div', class_='Location')
        subtitulo = subtitulo_tag.text.strip() if subtitulo_tag else None

        # Detalhes do imóvel
        detalhes_tag = imovel.find('div', class_='Details')
        metro_quadrado, quartos, vagas, banheiros = None, None, None, None
        if detalhes_tag:
            detalhes = detalhes_tag.find_all('div')
            metro_quadrado = re.sub(r'\D', '', detalhes[0].text) if detalhes else None
            quartos = re.sub(r'\D', '', detalhes[1].text) if len(detalhes) > 1 else None
            vagas = re.sub(r'\D', '', detalhes[2].text) if len(detalhes) > 2 else None
            banheiros = re.sub(r'\D', '', detalhes[3].text) if len(detalhes) > 3 else None

        return {
            'Link': link,
            'Preço': preco,
            'Título': titulo,
            'Subtítulo': subtitulo,
            'Metro Quadrado': metro_quadrado,
            'Quartos': quartos,
            'Vagas': vagas,
            'Banheiros': banheiros
        }

    except AttributeError as e:
        logging.warning(f'Erro ao extrair dados do imóvel: {e}')
        return None

def processar_conteudo_pagina(conteudo):
    """Processa o conteúdo HTML da página e extrai dados dos imóveis."""
    site = BeautifulSoup(conteudo, 'html.parser')
    imoveis = site.find_all('div', class_='content')
    data = [parsear_imovel(imovel) for imovel in imoveis]
    return [item for item in data if item]

def baixar_html(sessao, link):
    """Baixa o conteúdo HTML de um link específico e salva em um arquivo temporário."""
    try:
        response = sessao.get(link)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp_file:
            tmp_file.write(response.content)
            return tmp_file.name
    except requests.exceptions.RequestException as e:
        logging.error(f'Erro ao acessar o link {link}: {e}')
        return None

def extrair_informacoes_adicionais(filepath):
    """Extrai informações adicionais de um imóvel a partir do arquivo HTML salvo."""
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
        
        descricao_tag = soup.find('h2', class_='titulo-imovel-detalhe')
        descricao = descricao_tag.text.strip() if descricao_tag else None

        endereco_tag = soup.find('p', class_='endereco-caracteristicas')
        endereco = endereco_tag.text.strip() if endereco_tag else None

        # Suítes
        suites_tag = soup.find('div', class_='text title medium caracteristica-imovel', text=re.compile(r'\d+ Suítes'))
        suites = re.search(r'\d+', suites_tag.text).group(0) if suites_tag else None

        # Amenidades
        amenidades_tags = soup.find_all('div', class_='caracteristica-imovel-sobre')
        amenidades = [tag.text.strip() for tag in amenidades_tags]

        return {
            'Descrição': descricao,
            'Endereço': endereco,
            'Suítes': suites,
            'Amenidades': amenidades
        }
    except Exception as e:
        logging.error(f'Erro ao extrair dados do arquivo {filepath}: {e}')
        return None

def main():
    """Função principal que executa o scraping e processa os dados."""
    inicio = time.time()

    # Usando context manager para garantir que a sessão seja fechada corretamente
    with configurar_sessao() as sessao:
        todos_dados = []

        # Extrair dados das páginas
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(extrair_dados_pagina, sessao, pagina): pagina for pagina in range(1, 5)}  # Reduzindo para 5 páginas para teste
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Processando páginas"):
                conteudo = future.result()
                if conteudo:
                    todos_dados.extend(processar_conteudo_pagina(conteudo))

        # Filtrando dados nulos
        todos_dados = [dados for dados in todos_dados if dados]

        # Criação do DataFrame inicial
        df_imovel = pd.DataFrame(todos_dados)

        html_files = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(baixar_html, sessao, imovel['Link']): imovel['Link'] for imovel in todos_dados if imovel['Link']}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Baixando páginas adicionais"):
                html_file = future.result()
                if html_file:
                    html_files.append(html_file)

        # Extrair informações adicionais dos imóveis
        informacoes_adicionais = []
        for file in tqdm(html_files, desc="Processando informações adicionais"):
            info = extrair_informacoes_adicionais(file)
            if info:
                informacoes_adicionais.append(info)
            os.remove(file)  # Remove o arquivo temporário

        df_adicional = pd.DataFrame(informacoes_adicionais)

        # Tratamento das amenidades
        todas_amenidades = set(amenidade for sublist in df_adicional['Amenidades'] for amenidade in sublist)
        for amenidade in todas_amenidades:
            df_adicional[amenidade] = df_adicional['Amenidades'].apply(lambda x: 1 if amenidade in x else 0)
        df_adicional.drop(columns=['Amenidades'], inplace=True)

        # Merge dos DataFrames
        df_imovel = pd.concat([df_imovel, df_adicional], axis=1)

        # Função para limpar e converter colunas numéricas
        def limpar_converter_coluna(coluna):
            if coluna in df_imovel.columns:
                df_imovel[coluna] = pd.to_numeric(df_imovel[coluna], errors='coerce')
                df_imovel[coluna].fillna(0, inplace=True)

        # Limpeza e conversão das colunas numéricas
        colunas_numericas = ['Preço', 'Metro Quadrado', 'Quartos', 'Vagas', 'Banheiros', 'Suítes']
        for coluna in colunas_numericas:
            limpar_converter_coluna(coluna)

        # Salvando DataFrame final
        df_imovel.to_csv('imoveis_auxiliadora_predial.csv', index=False, encoding='utf-8-sig')

    fim = time.time()
    logging.info(f'Tempo total de execução: {fim - inicio:.2f} segundos')

if __name__ == '__main__':
    main()
