import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
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
    'Referer': 'https://www.creditoreal.com.br/',
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
    url = f'https://www.creditoreal.com.br/vendas?page={pagina}'
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
        titulo_elem = imovel.find('span', attrs={'class': 'sc-e9fa241f-1 fdybXW'})
        titulo = titulo_elem.text.strip() if titulo_elem else 'Título não disponível'

        link = 'https://www.creditoreal.com.br' + imovel['href'] if imovel['href'] else 'Link não disponível'

        subtitulo_elem = imovel.find('span', attrs={'class': 'sc-e9fa241f-1 hqggtn'})
        subtitulo = subtitulo_elem.text.strip() if subtitulo_elem else 'Subtítulo não disponível'

        tipo_elem = imovel.find('span', attrs={'class': 'sc-e9fa241f-0 bTpAju imovel-type'})
        tipo = tipo_elem.text.strip() if tipo_elem else 'Tipo não disponível'

        preco_elem = imovel.find('p', attrs={'class': 'sc-e9fa241f-1 ericyj'})
        preco = re.sub(r'\D', '', preco_elem.text) if preco_elem else '0'

        metro_area = imovel.find('div', attrs={'class': 'sc-b308a2c-2 iYXIja'})
        if metro_area:
            metro_text_elem = metro_area.find('p', attrs={'class': 'sc-e9fa241f-1 jUSYWw'})
            metro_text = metro_text_elem.text.strip() if metro_text_elem else ''
            metro_value = float(re.search(r'(\d+)', metro_text).group(1)) if re.search(r'(\d+)', metro_text) else 0
            if 'hectares' in metro_text.lower():
                metro_value *= 10000
        else:
            metro_value = 0

        quarto_vaga = metro_area.findAll('p', attrs={'class': 'sc-e9fa241f-1 jUSYWw'}) if metro_area else []
        quarto, vaga = 0, 0
        for item in quarto_vaga:
            text = item.text.lower()
            if 'quartos' in text:
                quarto = int(re.search(r'(\d+)', text).group(1)) if re.search(r'(\d+)', text) else 0
            elif 'vaga' in text:
                vaga = int(re.search(r'(\d+)', text).group(1)) if re.search(r'(\d+)', text) else 0

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

def processar_conteudo_pagina(conteudo):
    """Processa o conteúdo HTML da página e extrai dados dos imóveis."""
    site = BeautifulSoup(conteudo, 'html.parser')
    imoveis = site.findAll('a', attrs={'class': 'sc-613ef922-1 iJQgSL'})
    data = [parsear_imovel(imovel) for imovel in imoveis]  # Correção aqui
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
        
        endereco_elem = soup.find('span', attrs={'class': 'sc-e9fa241f-1 hqggtn'})
        endereco = endereco_elem.text.strip() if endereco_elem else 'Endereço não disponível'

        descricao_elem = soup.find('p', attrs={'class': 'sc-e9fa241f-1 fAJgAs'})
        descricao = descricao_elem.text.strip() if descricao_elem else 'Descrição não disponível'

        banheiro, suite, mobilia = 0, 0, 0
        detalhes = soup.findAll('p', attrs={'class': 'sc-e9fa241f-1 jUSYWw'})
        for detalhe in detalhes:
            texto = detalhe.text.lower()
            if 'banheiro' in texto:
                banheiro = int(re.search(r'(\d+)', texto).group(1)) if re.search(r'(\d+)', texto) else 0
            elif 'suite' in texto:
                suite = int(re.search(r'(\d+)', texto).group(1)) if re.search(r'(\d+)', texto) else 0
            elif 'mobilia' in texto:
                mobilia = 1 if 'sem' not in texto else 0

        div_amenidades = soup.find('div', attrs={'class': 'sc-b953b8ee-4 sFtII'})
        amenidades = [amenidade.text.strip() for amenidade in div_amenidades.findAll('div', attrs={'class': 'sc-c019b9bb-0 iZYuDq'})] if div_amenidades else []

        return {
            'Descrição': descricao,
            'Endereço': endereco,
            'Banheiro': banheiro,
            'Suíte': suite,
            'Mobilia': mobilia,
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
            futures = {executor.submit(extrair_dados_pagina, sessao, pagina): pagina for pagina in range(1, 3406)}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Processando páginas"):
                conteudo = future.result()
                if conteudo:
                    todos_dados.extend(processar_conteudo_pagina(conteudo))

        # Filtrando dados nulos
        todos_dados = [dado for dado in todos_dados if dado is not None]

        # Baixar HTML adicional e extrair informações adicionais
        with concurrent.futures.ThreadPoolExecutor(max_workers=13) as executor:
            futures = {executor.submit(baixar_html, sessao, dado['Link']): dado for dado in todos_dados}
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Baixando HTML adicional"):
                filepath = future.result()
                if filepath:
                    info_adicional = extrair_informacoes_adicionais(filepath)
                    if info_adicional:
                        dado_atual = futures[future]
                        dado_atual.update(info_adicional)
                    os.remove(filepath)  # Removendo arquivo temporário

        # Criando DataFrame e salvando em arquivo Excel
        df = pd.DataFrame(todos_dados)
        df.replace('', np.nan, inplace=True)
        df.to_excel('dados_imoveis.xlsx', index=False)

        fim = time.time()
        logging.info(f'Tempo total: {(fim - inicio) / 60:.2f} minutos')

if __name__ == "__main__":
    main()
