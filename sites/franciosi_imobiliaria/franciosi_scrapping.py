import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import concurrent.futures
from tqdm import tqdm
import re
import os
import logging
import numpy as np
import tempfile

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def configurar_sessao():
    sessao = requests.Session()
    sessao.headers.update(headers)
    adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
    sessao.mount('http://', adapter)
    sessao.mount('https://', adapter)
    return sessao

def extrair_dados_pagina(sessao, pagina, tentativas=3):
    url = f'https://www.franciosi.com.br/pesquisa-de-imoveis/?locacao_venda=V&id_cidade[]=26&finalidade=&dormitorio=&garagem=&vmi=&vma=&ordem=4&&pag={pagina}'
    for tentativa in range(tentativas):
        try:
            response = sessao.get(url)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            logging.error(f'Erro ao acessar a página {pagina}, tentativa {tentativa+1}/{tentativas}: {e}')
            time.sleep(2)
    return None

def parsear_imovel(imovel):
    try:
        link_tag = imovel.find('a', href=True)
        link = 'https://www.franciosi.com.br/' + link_tag['href'] if link_tag else None

        preco_tags = imovel.find('div', class_='card-valores')
        preco_venda, preco_aluguel = None, None
        if preco_tags:
            preco_text = preco_tags.text
            preco_venda = re.sub(r'\D', '', re.search(r'R\$ [\d.,]+ V', preco_text).group()) if re.search(r'R\$ [\d.,]+ V', preco_text) else None
            preco_aluguel = re.sub(r'\D', '', re.search(r'R\$ [\d.,]+ L', preco_text).group()) if re.search(r'R\$ [\d.,]+ L', preco_text) else None

        endereco_tag = imovel.find('p', class_='card-bairro-cidade my-1 pt-1')
        endereco_text = endereco_tag.text.strip() if endereco_tag else None
        bairro, cidade, estado = None, None, None
        if endereco_text:
            partes = endereco_text.split(' - ')
            if len(partes) == 2:
                bairro = partes[0].strip()
                cidade_estado = partes[1].split('/')
                if len(cidade_estado) == 2:
                    cidade = cidade_estado[0].strip()
                    estado = cidade_estado[1].strip()

        subtitulo_tag = imovel.find('p', class_='card-texto corta-card-desc my-4')
        subtitulo = subtitulo_tag.text.strip() if subtitulo_tag else None

        detalhes_tag = imovel.find_all('li', class_='list-group-item d-flex align-items-center justify-content-center card-itens')
        quartos, suites, banheiros, garagens = None, None, None, None
        if detalhes_tag:
            for detalhe in detalhes_tag:
                if 'Dorm.' in detalhe.get_text():
                    quartos = re.sub(r'\D', '', detalhe.find('span').text.strip())
                elif 'Suítes' in detalhe.get_text():
                    suites = re.sub(r'\D', '', detalhe.find('span').text.strip())
                elif 'Banho' in detalhe.get_text():
                    banheiros = re.sub(r'\D', '', detalhe.find('span').text.strip())
                elif 'Garagens' in detalhe.get_text():
                    garagens = re.sub(r'\D', '', detalhe.find('span').text.strip())

        return {
            'Link': link,
            'Preço Venda': preco_venda,
            'Preço Aluguel': preco_aluguel,
            'Bairro': bairro,
            'Cidade': cidade,
            'Estado': estado,
            'Subtítulo': subtitulo,
            'Quartos': quartos,
            'Suítes': suites,
            'Banheiros': banheiros,
            'Garagens': garagens
        }

    except AttributeError as e:
        logging.warning(f'Erro ao extrair dados do imóvel: {e}')
        return None

def processar_conteudo_pagina(conteudo):
    site = BeautifulSoup(conteudo, 'html.parser')
    imoveis = site.find_all('div', class_='card card-imo')
    data = [parsear_imovel(imovel) for imovel in imoveis]
    return [item for item in data if item]

def baixar_html(sessao, url, tentativas=3):
    for tentativa in range(tentativas):
        try:
            response = sessao.get(url)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp_file:
                tmp_file.write(response.content)
                return tmp_file.name
        except requests.exceptions.RequestException as e:
            logging.error(f'Erro ao baixar a página {url}, tentativa {tentativa+1}/{tentativas}: {e}')
            time.sleep(2)
    return None

def extrair_informacoes_adicionais(filepath):
    try:
        # First attempt to read the file with 'utf-8' encoding
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                soup = BeautifulSoup(file, 'html.parser')
        except UnicodeDecodeError:
            # If 'utf-8' decoding fails, fallback to 'latin-1' encoding
            with open(filepath, 'r', encoding='latin-1') as file:
                soup = BeautifulSoup(file, 'html.parser')

        titulo_tag = soup.find('div', class_='px-3 px-lg-0').find('h1', class_='titulo-imovel')
        titulo = titulo_tag.text.strip() if titulo_tag else None

        tipo_tag = soup.find('div', class_='col-6 col-md-4 col-lg-3 tipo-prop')
        tipo = tipo_tag.find('strong').text.strip() if tipo_tag else None

        codigo_tag = soup.find('div', class_='col-6 col-md-4 col-lg-3 codigo-imo')
        codigo = codigo_tag.find('span').text.strip() if codigo_tag else None

        area_terreno_tag = soup.find('div', class_='col-6 col-md-4 col-lg-3 a-terr-ico-imo')
        area_terreno = re.sub(r'\D', '', area_terreno_tag.find('strong').text) if area_terreno_tag else None

        area_construida_tag = soup.find('div', class_='col-6 col-md-4 col-lg-3 a-const-ico-imo')
        area_construida = re.sub(r'\D', '', area_construida_tag.find('strong').text) if area_construida_tag else None

        area_util_tag = soup.find('div', class_='col-6 col-md-4 col-lg-3 a-util-ico-imo')
        area_util = re.sub(r'\D', '', area_util_tag.find('strong').text) if area_util_tag else None

        amenidades_tags = soup.find_all('div', class_='itens-imo')
        amenidades = [tag.text.strip() for tag in amenidades_tags]

        return {
            'Link': filepath.split('_')[-1].split('.')[0],  # Extracting link ID from filename
            'Título': titulo,
            'Tipo': tipo,
            'Código': codigo,
            'Área Terreno': area_terreno,
            'Área Construída': area_construida,
            'Área Útil': area_util,
            'Amenidades': amenidades
        }
    except Exception as e:
        logging.error(f'Erro ao extrair dados do arquivo {filepath}: {e}')
        return None

def processar_amenidades(df, amenidades_col):
    todas_amenidades = set(amenidades for sublist in amenidades_col for amenidades in sublist)
    for amenidade in todas_amenidades:
        if amenidade:
            df[amenidade] = df['Amenidades'].apply(lambda x: 1 if amenidade in x else 0)

def limpar_converter_coluna(df, coluna):
    if coluna in df.columns:
        df[coluna] = df[coluna].str.replace('.', '').str.replace(',', '').str.extract(r'(\d+)').astype(float)
        df[coluna].fillna(0, inplace=True)

def main():
    inicio = time.time()

    sessao = configurar_sessao()
    todos_dados = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(extrair_dados_pagina, sessao, pagina): pagina for pagina in range(1, 200)}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Processando páginas"):
            conteudo = future.result()
            if conteudo:
                dados_pagina = processar_conteudo_pagina(conteudo)
                todos_dados.extend(dados_pagina)

    df_imovel = pd.DataFrame(todos_dados)

    html_files = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(baixar_html, sessao, imovel['Link']): imovel['Link'] for imovel in todos_dados if imovel['Link']}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Baixando páginas adicionais"):
            html_file = future.result()
            if html_file:
                html_files.append(html_file)

    informacoes_adicionais = []
    for file in tqdm(html_files, desc="Processando informações adicionais"):
        info = extrair_informacoes_adicionais(file)
        if info:
            informacoes_adicionais.append(info)
        os.remove(file)

    df_adicional = pd.DataFrame(informacoes_adicionais)

    if not df_adicional.empty and 'Link' in df_adicional.columns:
        df_adicional.set_index('Link', inplace=True)
        if 'Amenidades' in df_adicional.columns:
            processar_amenidades(df_adicional, df_adicional['Amenidades'])

    if 'Link' in df_imovel.columns and 'Link' in df_adicional.columns:
        df_completo = pd.merge(df_imovel, df_adicional, on='Link', how='left')
        df_completo = df_completo.loc[:, ~df_completo.columns.duplicated()]

        colunas_numericas = ['Preço Venda', 'Preço Aluguel', 'Área Terreno', 'Área Construída', 'Área Útil', 'Quartos', 'Garagens', 'Banheiros', 'Suítes']
        for coluna in colunas_numericas:
            limpar_converter_coluna(df_completo, coluna)

        df_completo['M2 Venda'] = df_completo.apply(lambda row: row['Preço Venda'] / row['Área Terreno'] if row['Área Terreno'] > 0 else 0, axis=1)
        df_completo['M2 Aluguel'] = df_completo.apply(lambda row: row['Preço Aluguel'] / row['Área Terreno'] if row['Área Terreno'] > 0 else 0, axis=1)

        df_completo.to_excel('imoveis_franciosi.xlsx', index=False, engine='openpyxl')

    fim = time.time()
    logging.info(f'Tempo total de execução: {fim - inicio:.2f} segundos')

if __name__ == '__main__':
    main()
