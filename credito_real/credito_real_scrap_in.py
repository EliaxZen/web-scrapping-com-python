import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import numpy as np
import time
import logging
import asyncio
import aiohttp
from aiohttp import ClientSession
import random

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Lista de User-Agents para rotação
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0'
]

# Lista para registrar URLs com erro
urls_com_erro = []

async def extrair_dados_pagina(sessao: ClientSession, pagina: int):
    url = f'https://www.creditoreal.com.br/vendas?page={pagina}'
    headers = {'User-Agent': random.choice(USER_AGENTS), 'Referer': 'https://www.creditoreal.com.br/'}
    try:
        async with sessao.get(url, headers=headers) as resposta:
            resposta.raise_for_status()
            await asyncio.sleep(random.uniform(8, 10))  # Espera aleatória entre 2 a 5 segundos
            return await resposta.text()
    except aiohttp.ClientError as e:
        logging.error(f'Erro ao acessar a página {pagina}: {e}. Pulando para a próxima página.')
        urls_com_erro.append(url)
        return None

async def extrair_detalhes_imovel(sessao: ClientSession, link: str):
    headers = {'User-Agent': random.choice(USER_AGENTS), 'Referer': 'https://www.creditoreal.com.br/'}
    try:
        async with sessao.get(link, headers=headers) as resposta:
            if resposta.status == 404:
                urls_com_erro.append(link)
                logging.error(f'Erro ao acessar o detalhe do imóvel {link}: 404 Not Found')
                return None, None, None, None, 0, []
            resposta.raise_for_status()
            conteudo = await resposta.text()
            soup = BeautifulSoup(conteudo, 'html.parser')

            endereco = soup.find('span', attrs={'class': 'sc-e9fa241f-1 hqggtn'})
            descricao = soup.find('p', attrs={'class': 'sc-e9fa241f-1 fAJgAs'})

            endereco_texto = endereco.text.strip() if endereco else None
            descricao_texto = descricao.text.strip() if descricao else None

            banheiro = None
            suite = None
            mobilia = 0

            # Extrair banheiros, suítes e mobília
            detalhes = soup.findAll('p', attrs={'class': 'sc-e9fa241f-1 jUSYWw'})
            for detalhe in detalhes:
                texto = detalhe.text.lower()
                if 'banheiro' in texto:
                    banheiro = re.search(r'(\d+)', texto).group(1)
                elif 'suíte' in texto:
                    suite = re.search(r'(\d+)', texto).group(1)
                elif 'mobilia' in texto:
                    mobilia = 1 if 'sem' not in texto else 0

            # Extrair amenities
            div_amenidades = soup.find('div', attrs={'class': 'sc-b953b8ee-4 sFtII'})
            amenidades = [amenidade.text.strip() for amenidade in div_amenidades.findAll('div', attrs={'class': 'sc-c019b9bb-0 iZYuDq'})] if div_amenidades else []

            return descricao_texto, endereco_texto, banheiro, suite, mobilia, amenidades

    except aiohttp.ClientError as e:
        logging.error(f'Erro ao acessar o detalhe do imóvel {link}: {e}. Pulando para o próximo imóvel.')
        urls_com_erro.append(link)
        return None, None, None, None, 0, []

async def parse_imovel(sessao: ClientSession, imovel):
    titulo = imovel.find('span', attrs={'class': 'sc-e9fa241f-1 fdybXW'})
    link = 'https://www.creditoreal.com.br' + imovel['href']
    subtitulo = imovel.find('span', attrs={'class': 'sc-e9fa241f-1 hqggtn'})
    tipo = imovel.find('span', attrs={'class': 'sc-e9fa241f-0 bTpAju imovel-type'})
    preco = imovel.find('p', attrs={'class': 'sc-e9fa241f-1 ericyj'})

    area_metro = imovel.find('div', attrs={'class': 'sc-b308a2c-2 iYXIja'})
    if area_metro is not None:
        metro = area_metro.find('p', attrs={'class': 'sc-e9fa241f-1 jUSYWw'})
        if metro:
            metro_texto = metro.text.strip()
            if 'hectares' in metro_texto.lower():
                metro_valor = float(re.search(r'(\d+)', metro_texto).group(1)) * 10000
            else:
                metro_valor = float(re.search(r'(\d+)', metro_texto).group(1))
        else:
            metro_valor = None
    else:
        metro_valor = None

    quarto_vaga = imovel.find('div', attrs={'class': 'sc-b308a2c-2 iYXIja'})
    quarto = vaga = None
    if quarto_vaga:
        lista = quarto_vaga.findAll('p', attrs={'class': 'sc-e9fa241f-1 jUSYWw'})
        for item in lista:
            if 'quartos' in item.text.lower():
                quarto = re.search(r'(\d+)', item.text).group(1)
            elif 'vaga' in item.text.lower():
                vaga = re.search(r'(\d+)', item.text).group(1)

    if titulo and subtitulo and preco and metro_valor:
        preco_valor = re.sub(r'\D', '', preco.text)
        if preco_valor and metro_valor:
            descricao, endereco, banheiro, suite, mobilia, amenidades = await extrair_detalhes_imovel(sessao, link)
            return [titulo.text.strip(), subtitulo.text.strip(), link, preco_valor, metro_valor, quarto, vaga, tipo.text, descricao, endereco, banheiro, suite, mobilia, amenidades]
    return None

async def processar_conteudo_pagina(sessao: ClientSession, conteudo):
    site = BeautifulSoup(conteudo, 'html.parser')
    imoveis = site.findAll('a', attrs={'class': 'sc-613ef922-1 iJQgSL'})
    tarefas = [parse_imovel(sessao, imovel) for imovel in imoveis]
    dados = await asyncio.gather(*tarefas)
    return [item for item in dados if item]

async def main():
    inicio = time.time()
    async with aiohttp.ClientSession() as sessao:
        todos_dados = []

        tarefas_paginas = [extrair_dados_pagina(sessao, pagina) for pagina in range(1, 3405)]
        conteudos_paginas = await asyncio.gather(*tarefas_paginas)

        for conteudo in conteudos_paginas:
            if conteudo:
                todos_dados.extend(await processar_conteudo_pagina(sessao, conteudo))

    df_imoveis = pd.DataFrame(todos_dados, columns=['Título', 'Subtítulo', 'Link', 'Preço', 'Metro Quadrado', 'Quarto', 'Vaga', 'Tipo', 'Descrição', 'Endereço', 'Banheiro', 'Suíte', 'Mobília', 'Amenidades'])

    # Converte as colunas para valores numéricos, preenchendo com NaN onde não for possível
    df_imoveis['Preço'] = pd.to_numeric(df_imoveis['Preço'], errors='coerce')
    df_imoveis['Metro Quadrado'] = pd.to_numeric(df_imoveis['Metro Quadrado'], errors='coerce')
    df_imoveis['Quarto'] = pd.to_numeric(df_imoveis['Quarto'], errors='coerce')
    df_imoveis['Vaga'] = pd.to_numeric(df_imoveis['Vaga'], errors='coerce')
    df_imoveis['Banheiro'] = pd.to_numeric(df_imoveis['Banheiro'], errors='coerce')
    df_imoveis['Suíte'] = pd.to_numeric(df_imoveis['Suíte'], errors='coerce')
    df_imoveis['Mobília'] = pd.to_numeric(df_imoveis['Mobília'], errors='coerce')

    fim = time.time()
    logging.info(f'Processamento concluído em {fim - inicio} segundos')
    return df_imoveis, urls_com_erro

if __name__ == '__main__':
    asyncio.run(main())
