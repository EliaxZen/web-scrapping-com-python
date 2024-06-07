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
    url = f'https://www.creditoreal.com.br/alugueis/porto-alegre-rs?cityState=porto-alegre-rs&page={pagina}'
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
            elif 'suite' in texto:
                suite = re.search(r'(\d+)', texto).group(1)
            elif 'mobilia' in texto:
                mobilia = 1 if 'Sem' not in texto else 0

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
            futures = {executor.submit(extrair_dados_pagina, sessao, pagina): pagina for pagina in range(1, 300)}
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
            futures = {executor.submit(baixar_html, sessao, imovel['Link']): imovel['Link'] for imovel in todos_dados}
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
        colunas_numericas = ['Preço', 'Metro Quadrado', 'Quarto', 'Vaga', 'Banheiro', 'Suíte', 'Mobilia']
        for coluna in colunas_numericas:
            limpar_converter_coluna(coluna)

        # Adiciona nova coluna 'M2' e calcula a divisão
        df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Metro Quadrado']
        df_imovel['M2'].fillna(0, inplace=True)

        # Reordenar colunas
        colunas_ordem = ['Título', 'Subtítulo', 'Link', 'Preço', 'Metro Quadrado', 'Quarto', 'Vaga', 'Banheiro', 'Suíte', 'Mobilia', 'Tipo', 'Descrição', 'Endereço', 'M2'] + list(todas_amenidades)
        df_imovel = df_imovel[colunas_ordem]

        fim = time.time()
        logging.info(f'Tempo total: {fim - inicio:.2f} segundos')

        # Salvando o DataFrame final em um arquivo Excel
        df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\base_de_dados_excel\credito_real_data_base\credito_real_porto_alegre_aluguel_06_2024.xlsx', index=False)

if __name__ == "__main__":
    main()
