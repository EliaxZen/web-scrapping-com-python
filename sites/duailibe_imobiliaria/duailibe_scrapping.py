import time
import pandas as pd
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from tqdm import tqdm
import re

# Configuração de logging
logging.basicConfig(level=logging.INFO)

# Inicializar o navegador com Selenium
service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(service=service, options=options)

# Navegar até a página principal
url = "https://www.duailibeimobiliaria.com.br/imoveis/a-venda"
driver.get(url)

# Função para carregar mais imóveis
def carregar_mais_imoveis(quantidade_cliques):
    for _ in range(quantidade_cliques):
        try:
            # Número de imóveis antes do clique
            num_imoveis_antes = len(driver.find_elements(By.CSS_SELECTOR, "div.card.card-listing"))
            logging.info(f"Número de imóveis antes do clique: {num_imoveis_antes}")
            
            load_more_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.pagination-cell button.btn.btn-md.btn-primary.btn-next"))
            )
            driver.execute_script("arguments[0].click();", load_more_button)
            
            # Esperar até que novos imóveis sejam carregados
            WebDriverWait(driver, 30).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "div.card.card-listing")) > num_imoveis_antes
            )
        except Exception as e:
            logging.error(f"Erro ao carregar mais imóveis: {e}")
            break

# Definir a quantidade de vezes que deseja clicar no botão de carregar mais imóveis
quantidade_cliques = 100  # Aumentar a quantidade de cliques
carregar_mais_imoveis(quantidade_cliques)

# Esperar um pouco mais para garantir que todos os imóveis sejam carregados
time.sleep(10)

# Extrair informações básicas dos imóveis
soup = BeautifulSoup(driver.page_source, 'html.parser')
imoveis = soup.find_all('div', class_='card card-listing')
logging.info(f"Total de imóveis encontrados: {len(imoveis)}")

# Lista para armazenar os dados
data = []

# URL base para links
url_base = "https://www.duailibeimobiliaria.com.br"

# Função para extrair texto ou retornar None
def get_text_or_none(element):
    return element.text.strip() if element else None

# Função para limpar e converter preço para número
def limpar_preco(preco):
    preco_limpo = re.sub(r'[^\d]', '', preco)
    return float(preco_limpo) if preco_limpo else None

# Função para extrair informações básicas de composição
def extrair_informacoes_composicao(composicao):
    quartos_match = re.search(r'(\d+)\s*quartos', composicao)
    suite_match = re.search(r'(\d+)\s*suíte', composicao)
    banheiros_match = re.search(r'(\d+)\s*banheiros', composicao)
    vagas_match = re.search(r'(\d+)\s*vaga', composicao)
    area_match = re.search(r'([\d,]+)\s*m²', composicao)

    # Capturando os valores ou definindo como '0' se não forem encontrados
    quartos = quartos_match.group(1) if quartos_match else '0'
    suite = suite_match.group(1) if suite_match else '0'
    banheiros = banheiros_match.group(1) if banheiros_match else '0'
    vagas = vagas_match.group(1) if vagas_match else '0'
    area = area_match.group(1).replace(',', '.') if area_match else '0'

    return quartos, suite, banheiros, vagas, area

# Iterar sobre cada imóvel e extrair as informações básicas
for imovel in tqdm(imoveis, desc="Extraindo informações dos imóveis"):
    try:
        link_tag = imovel.find('a', href=True)
        link = url_base + link_tag['href'] if link_tag else None
        titulo = get_text_or_none(imovel.find('h2', class_='card-title'))
        endereco = get_text_or_none(imovel.find('h3', class_='card-text'))
        descricao = get_text_or_none(imovel.find('p', class_='description hidden-sm-down'))
        
        # Extrair todos os preços e classificá-los como venda
        precos = imovel.select('div.info-left span.h-money.location')
        preco_venda = None
        for preco in precos:
            preco_text = get_text_or_none(preco)
            if 'mês' not in preco_text:
                preco_venda = preco_text

        preco_condominio = get_text_or_none(imovel.select_one('div.info-right span.h-money:nth-child(1)'))
        preco_iptu = get_text_or_none(imovel.select_one('div.info-right span.h-money:nth-child(2)'))
        composicao = get_text_or_none(imovel.find('div', class_='values'))
        
        # Verificar se a composição foi encontrada antes de processar
        if composicao:
            quartos, suite, banheiros, vagas, area = extrair_informacoes_composicao(composicao)
        else:
            quartos, suite, banheiros, vagas, area = '0', '0', '0', '0', '0'

        logging.info(f"Imóvel encontrado: {titulo} - {endereco}")

        preco_venda_num = limpar_preco(preco_venda) if preco_venda else None
        preco_condominio_num = limpar_preco(preco_condominio) if preco_condominio else 0
        preco_iptu_num = limpar_preco(preco_iptu) if preco_iptu else 0
        area_num = float(area) if area else 0

        logging.info(f"Preços e área extraídos: Venda - {preco_venda_num}, Condomínio - {preco_condominio_num}, IPTU - {preco_iptu_num}, Área - {area_num}")

        # Somente adicionar o imóvel se o preço de venda for válido
        if preco_venda_num:
            data.append({
                'Título': titulo,
                'Link': link,
                'Endereço': endereco,
                'Descrição': descricao,
                'Preço Venda': preco_venda_num,
                'Preço Condomínio': preco_condominio_num,
                'Preço IPTU': preco_iptu_num,
                'Área': area_num,
                'Quartos': int(quartos) if quartos else 0,
                'Suíte': int(suite) if suite else 0,
                'Banheiros': int(banheiros) if banheiros else 0,
                'Vagas': int(vagas) if vagas else 0,
                'M2 Venda': preco_venda_num / area_num if area_num != 0 else 0
            })
    except Exception as e:
        logging.error(f"Erro ao processar o imóvel: {e}")

# Fechar o navegador
driver.quit()

# Criar o DataFrame
df = pd.DataFrame(data)

# Reordenar as colunas
colunas = [
    'Título', 'Link', 'Endereço', 'Descrição', 'Preço Venda', 
    'Preço Condomínio', 'Preço IPTU', 'Área', 'Quartos', 'Suíte', 
    'Banheiros', 'Vagas', 'M2 Venda'
]
df = df[colunas]

# Remover imóveis que possuem preço de venda inválido (zero ou nulo)
df = df[df['Preço Venda'] > 0]

# Salvar em um arquivo Excel
df.to_excel('imoveis_duailibe.xlsx', index=False)

logging.info("Dados salvos com sucesso!")
