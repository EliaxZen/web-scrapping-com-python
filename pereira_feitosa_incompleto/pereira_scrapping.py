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
url = "https://www.pereirafeitosa.com.br/imoveis/a-venda"
driver.get(url)
logging.info("Página carregada.")

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
            logging.info("Botão 'Ver mais' clicado.")

            # Esperar até que novos imóveis sejam carregados
            WebDriverWait(driver, 30).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "div.card.card-listing")) > num_imoveis_antes
            )
            logging.info("Novos imóveis carregados.")
        except Exception as e:
            logging.error(f"Erro ao carregar mais imóveis: {e}")
            break

# Definir a quantidade de vezes que deseja clicar no botão de carregar mais imóveis
quantidade_cliques = 5
carregar_mais_imoveis(quantidade_cliques)

# Esperar um pouco mais para garantir que todos os imóveis sejam carregados
time.sleep(10)

# Extrair informações básicas dos imóveis
soup = BeautifulSoup(driver.page_source, 'html.parser')
imoveis = soup.find_all('div', class_='card card-listing')
logging.info(f"Total de imóveis encontrados: {len(imoveis)}")

# Imprimir o HTML da página carregada para inspeção
with open('pagina_carregada.html', 'w', encoding='utf-8') as file:
    file.write(soup.prettify())

# Lista para armazenar os dados
data = []

# URL base para links
url_base = "https://www.pereirafeitosa.com.br/"

# Função para extrair texto ou retornar None
def get_text_or_none(element):
    return element.text.strip() if element else None

# Função para limpar e converter preço para número
def limpar_preco(preco):
    preco_limpo = re.sub(r'[^\d]', '', preco)
    return float(preco_limpo) if preco_limpo else None

# Função para extrair informações básicas de composição
def extrair_informacoes_composicao(imovel):
    quartos = get_text_or_none(imovel.find('div', class_='value', text=re.compile('quartos')))
    suite = get_text_or_none(imovel.find('div', class_='value', text=re.compile('suíte')))
    banheiros = get_text_or_none(imovel.find('div', class_='value', text=re.compile('banheiros')))
    vagas = get_text_or_none(imovel.find('div', class_='value', text=re.compile('vaga')))
    area = get_text_or_none(imovel.find('div', class_='value', text=re.compile('m²')))
    return quartos, suite, banheiros, vagas, area

# Iterar sobre cada imóvel e extrair as informações básicas
for imovel in tqdm(imoveis, desc="Extraindo informações dos imóveis"):
    try:
        link_tag = imovel.find('a', href=True)
        link = url_base + link_tag['href'] if link_tag else None
        titulo = get_text_or_none(imovel.find('h2', class_='card-title'))
        endereco = get_text_or_none(imovel.find('h3', class_='card-text'))
        descricao = get_text_or_none(imovel.find('p', class_='description hidden-sm-down'))

        preco_venda = get_text_or_none(imovel.select_one('div.info-left span.h-money.location'))
        preco_condominio = get_text_or_none(imovel.select_one('div.info-right span.h-money:nth-child(1)'))
        preco_iptu = get_text_or_none(imovel.select_one('div.info-right span.h-money:nth-child(2)'))

        quartos, suite, banheiros, vagas, area = extrair_informacoes_composicao(imovel)
        
        logging.info(f"Imóvel encontrado: {titulo} - {endereco}")

        preco_venda_num = limpar_preco(preco_venda) if preco_venda else None
        preco_condominio_num = limpar_preco(preco_condominio) if preco_condominio else 0
        preco_iptu_num = limpar_preco(preco_iptu) if preco_iptu else 0
        area_num = float(area.replace(',', '.')) if area else 0

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

# Verificar se dados foram extraídos
if data:
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
    df.to_excel('imoveis_pereira.xlsx', index=False)
    logging.info("Dados salvos com sucesso!")
else:
    logging.error("Nenhum imóvel foi encontrado ou extraído.")
