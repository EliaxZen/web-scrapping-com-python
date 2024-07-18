import re
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from distrito_federal_setor import setores
import concurrent.futures
import logging
from random import randint, choice
from typing import List, Dict

# Configurações de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurações
TEMPO_ESPERA = 3  # Aumenta o tempo de espera entre requisições
NUM_PAGINAS = 10
URL_BASE = "https://www.imovelweb.com.br"
ARQUIVO_SAIDA = r"C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\base_de_dados_excel\imovel_web_data_base\imovel_web_aluguel_df_05_2024.xlsx"

# Lista de User-Agents para rotação
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0",
    # Adicione outros User-Agents conforme necessário
]

HEADERS = {
    "User-Agent": choice(USER_AGENTS),
    "Referer": "https://www.imovelweb.com.br/",
}

# Lista de proxies reais (testados)
PROXIES = [
    'http://104.248.63.15:30588',
    'http://45.76.176.138:8080',
    'http://159.89.49.132:8080',
    'http://46.101.26.4:39313',
    'http://64.225.8.115:9989',
    'http://178.62.193.19:8080',
    'http://64.225.97.57:8080',
    'http://46.101.53.59:8080',
    'http://167.172.236.149:39313',
    'http://167.172.236.149:39313',
    # Adicione mais proxies conforme necessário
]

def extrair_setor(titulo: str) -> str:
    """Extrai o setor a partir do título do imóvel."""
    palavras = titulo.split()
    palavras_upper = [palavra.upper() for palavra in palavras]
    for palavra in palavras_upper:
        if palavra in setores:
            return palavra
    return "OUTRO"

def extrair_tipo(link: str) -> str:
    """Extrai o tipo de imóvel a partir do link."""
    tipos = {
        "apartamento": "Apartamento",
        "casa": "Casa",
        "casa-condominio": "Casa Condomínio",
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
        "lote": "Lote/Terreno",
        "galpao": "Galpão",
        "comercial": "Comercial",
        "fazenda": "Fazenda",
        "chacara": "Chácara",
        "condominio": "Condomínio",
        "kit": "Kitnet",
        "hotel": "Hotel",
        "residencial": "Residencial",
    }
    for key, value in tipos.items():
        if key in link:
            return value
    return "OUTROS"

def obter_dados_imovel(imovel: BeautifulSoup) -> Dict[str, str]:
    """Extrai os dados de um imóvel."""
    titulo = imovel.find("div", class_="LocationAddress-sc-ge2uzh-0 iylBOA postingAddress")
    link = URL_BASE + imovel["data-to-posting"]
    subtitulo = imovel.find("h2", attrs={"data-qa": "POSTING_CARD_LOCATION"})
    imobiliaria_element = imovel.find("img", attrs={"data-qa": "POSTING_CARD_PUBLISHER"})
    imobiliaria = imobiliaria_element["src"] if imobiliaria_element else None
    preco = imovel.find("div", attrs={"data-qa": "POSTING_CARD_PRICE"})
    condominio = imovel.find("div", attrs={"data-qa": "expensas"})
    metro_area = imovel.find("h3", attrs={"data-qa": "POSTING_CARD_FEATURES"})
    metro = metro_area.find("span") if metro_area else None
    quarto_banheiro_vaga = imovel.find("h3", attrs={"data-qa": "POSTING_CARD_FEATURES"})

    quarto = banheiro = vaga = None
    if quarto_banheiro_vaga:
        lista = quarto_banheiro_vaga.findAll("span")
        for item in lista:
            texto = item.text.lower()
            if "quartos" in texto:
                quarto = item.text
            elif "ban." in texto:
                banheiro = item.text
            elif "vaga" in texto:
                vaga = item.text

    return {
        "Título": titulo.text.strip() if titulo else None,
        "Subtítulo": subtitulo.text.strip() if subtitulo else None,
        "Link": link,
        "Preço": preco.text if preco else None,
        "Área": metro.text.replace(" m² tot.", "").strip() if metro else None,
        "Quarto": quarto,
        "Banheiro": banheiro,
        "Vaga": vaga,
        "Imobiliária": imobiliaria,
    }

def obter_pagina(url: str, session: requests.Session) -> BeautifulSoup:
    """Obtém o conteúdo de uma página."""
    headers = HEADERS.copy()
    headers["User-Agent"] = choice(USER_AGENTS)  # Rotaciona o User-Agent a cada requisição
    proxy = {"http": choice(PROXIES), "https": choice(PROXIES)}  # Seleciona um proxy aleatório
    for _ in range(3):  # Tentar 3 vezes
        try:
            resposta = session.get(url, headers=headers, proxies=proxy, timeout=10)  # Adicionado timeout
            resposta.raise_for_status()
            return BeautifulSoup(resposta.content, "html.parser")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Erro ao acessar a página: {e}")
            time.sleep(TEMPO_ESPERA + randint(1, 3))  # Espera um tempo aleatório
    return None

def obter_lista_de_imoveis(paginas: int = NUM_PAGINAS, tempo_espera: int = TEMPO_ESPERA) -> List[Dict[str, str]]:
    """Obtém a lista de imóveis de várias páginas."""
    lista_de_imoveis = []
    urls_adicionados = set()

    with requests.Session() as session:
        session.headers.update(HEADERS)
        urls = [f"{URL_BASE}/imoveis-aluguel-distrito-federal-pagina-{pagina}.html" for pagina in range(1, paginas + 1)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {executor.submit(obter_pagina, url, session): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    site = future.result()
                    if site:
                        imoveis = site.findAll("div", attrs={"data-qa": "posting PROPERTY"})
                        for imovel in imoveis:
                            dados_imovel = obter_dados_imovel(imovel)
                            if (
                                dados_imovel["Título"]
                                and dados_imovel["Subtítulo"]
                                and dados_imovel["Preço"]
                                and dados_imovel["Área"]
                                and "Sob Consulta" not in dados_imovel["Preço"]
                                and dados_imovel["Link"] not in urls_adicionados
                            ):
                                lista_de_imoveis.append(dados_imovel)
                                urls_adicionados.add(dados_imovel["Link"])
                            else:
                                logging.info("Imóvel ignorado devido a dados ausentes ou preço 'Sob Consulta'")
                except Exception as e:
                    logging.error(f"Erro ao processar página {url}: {e}")

                time.sleep(tempo_espera + randint(1, 3))  # Espera um tempo aleatório
    return lista_de_imoveis

def processar_dados(lista_de_imoveis: List[Dict[str, str]]) -> pd.DataFrame:
    """Processa os dados e retorna um DataFrame."""
    df = pd.DataFrame(lista_de_imoveis)
    df["Área"] = df["Área"].str.replace(" m²", "", regex=False)
    df["Preço"] = df["Preço"].str.replace("R\$", "", regex=False).str.replace(".", "", regex=False).str.strip()
    df["Setor"] = df["Título"].apply(extrair_setor)
    df["Tipo"] = df["Link"].apply(extrair_tipo)
    df = df[df["Setor"].isin(setores)]
    df["Preço"] = df["Preço"].str.extract("(\d+)").astype(float)
    df["Área"] = df["Área"].astype(float)
    df["Preço_m2"] = df["Preço"] / df["Área"]
    return df

def main():
    logging.info("Iniciando o processo de scraping.")
    lista_de_imoveis = obter_lista_de_imoveis()
    logging.info(f"Total de imóveis coletados: {len(lista_de_imoveis)}")
    df = processar_dados(lista_de_imoveis)
    df.to_excel(ARQUIVO_SAIDA, index=False)
    logging.info(f"Dados salvos em {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    main()
