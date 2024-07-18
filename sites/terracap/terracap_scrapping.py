import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuração do logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def validate_parameters(start_year, start_month, end_year, end_month):
    """Valida os parâmetros de entrada."""
    if start_year > end_year or (start_year == end_year and start_month > end_month):
        raise ValueError("A data inicial deve ser anterior ou igual à data final.")
    if start_month < 1 or start_month > 12 or end_month < 1 or end_month > 12:
        raise ValueError("Os meses devem estar entre 1 e 12.")

def generate_urls(start_year, start_month, end_year, end_month):
    """Gera uma lista de URLs baseadas nos anos e meses fornecidos."""
    validate_parameters(start_year, start_month, end_year, end_month)
    
    urls = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            if (year == start_year and month < start_month) or (year == end_year and month > end_month):
                continue
            urls.append(f"https://comprasonline.terracap.df.gov.br/bidding/external/index?edict_year={year}&edict_number={month}")
    return urls

def extract_text(element):
    """Extrai texto de um elemento, retornando None se o elemento for None."""
    return element.get_text(strip=True) if element else None

def extract_data_from_box(box):
    """Extrai dados de uma caixa de informações de imóvel."""
    status_element = box.select_one('.extra.content .ui.button')
    status = extract_text(status_element).split()[0] if status_element else None

    item_edital_element = box.select_one('.image h1')
    item_edital = extract_text(item_edital_element)

    edital_element = box.select_one('.header')
    edital = extract_text(edital_element).split(': ')[1] if edital_element and ': ' in extract_text(edital_element) else None

    endereco_element = box.select_one('.description.truncate')
    endereco = extract_text(endereco_element).split(': ')[1] if endereco_element and ': ' in extract_text(endereco_element) else None

    licitante_element = box.select_one('.description:-soup-contains("Licitante")')
    licitante = extract_text(licitante_element).split(': ')[1] if licitante_element and ': ' in extract_text(licitante_element) else None

    valor_element = box.select_one('.description:-soup-contains("Valor")')
    valor = extract_text(valor_element).split(': ')[1].replace('R$ ', '').replace('.', '').replace(',', '.') if valor_element and ': ' in extract_text(valor_element) else None

    condicao_element = box.select_one('.description:-soup-contains("Condição")')
    condicao = extract_text(condicao_element).split(': ')[1] if condicao_element and ': ' in extract_text(condicao_element) else None

    meses_element = box.select_one('.description:-soup-contains("Meses")')
    meses = extract_text(meses_element).split(': ')[1] if meses_element and ': ' in extract_text(meses_element) else None

    entrada_element = box.select_one('.description:-soup-contains("Entrada")')
    entrada = extract_text(entrada_element).split(': ')[1].replace('%', '').replace(',', '.') if entrada_element and ': ' in extract_text(entrada_element) else None

    # Adiciona ao dicionário apenas se o valor não for None ou zero
    if valor:
        return {
            'Status': status,
            'Item Edital': item_edital,
            'Edital': edital,
            'Endereço': endereco,
            'Licitante': licitante,
            'Valor': valor,
            'Condição': condicao,
            'Meses': meses,
            'Entrada': entrada
        }
    return None

def scrape_terrap(url):
    """Faz scraping de uma URL específica."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        logging.info(f"Acessando a URL: {url}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        property_boxes = soup.select('.ui.link.cards.centered .card')
        
        data = [extract_data_from_box(box) for box in property_boxes]
        data = [d for d in data if d]  # Remove entradas None
        return pd.DataFrame(data)
    except requests.RequestException as e:
        logging.error(f"Erro ao acessar a URL {url}: {e}")
    except Exception as e:
        logging.error(f"Erro ao processar os dados da URL {url}: {e}")
    return pd.DataFrame()

def main(start_year, start_month, end_year, end_month, output_file):
    """Executa o scraping em paralelo e salva os dados em um arquivo Excel."""
    urls = generate_urls(start_year, start_month, end_year, end_month)
    all_dfs = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(scrape_terrap, url): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                df = future.result()
                if not df.empty:
                    all_dfs.append(df)
            except Exception as e:
                logging.error(f"Erro ao processar a URL {url}: {e}")

    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        final_df['Valor'] = pd.to_numeric(final_df['Valor'], errors='coerce')
        final_df['Meses'] = pd.to_numeric(final_df['Meses'], errors='coerce')
        final_df['Entrada'] = pd.to_numeric(final_df['Entrada'], errors='coerce') / 100
        final_df['Item Edital'] = pd.to_numeric(final_df['Item Edital'], errors='coerce')
        final_df['Licitante'] = pd.to_numeric(final_df['Licitante'], errors='coerce')
        final_df.to_excel(output_file, index=False)
        logging.info(f"Dados salvos com sucesso em '{output_file}'.")
    else:
        logging.warning("Nenhum dado foi extraído.")

# Parâmetros de entrada: ano inicial, mês inicial, ano final, mês final e nome do arquivo de saída
start_year = 2000
start_month = 1
end_year = 2024
end_month = 6
output_file = 'imoveis_licitacao.xlsx'

if __name__ == "__main__":
    main(start_year, start_month, end_year, end_month, output_file)
