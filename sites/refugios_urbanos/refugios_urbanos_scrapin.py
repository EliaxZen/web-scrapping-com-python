import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from tqdm import tqdm
import re

# Inicializar o navegador com Selenium
service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(service=service, options=options)

# Navegar até a página principal
url = "https://refugiosurbanos.com.br/imoveis/"
driver.get(url)

# Função para fechar o banner, se ele aparecer
def fechar_banner():
    try:
        close_button = driver.find_element(By.CSS_SELECTOR, 'button.pum-close.popmake-close')
        close_button.click()
        print("Banner fechado.")
    except Exception as e:
        pass  # Se o banner não estiver presente, não fazer nada

# Função para carregar mais imóveis
def carregar_mais_imoveis(quantidade_cliques):
    for _ in range(quantidade_cliques):
        try:
            fechar_banner()  # Fechar o banner se aparecer
            
            # Número de imóveis antes do clique
            num_imoveis_antes = len(driver.find_elements(By.CSS_SELECTOR, "article.imovel.galeria-imoveis-thumb"))
            print(num_imoveis_antes)
            
            load_more_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#paginador a"))
            )
            driver.execute_script("arguments[0].click();", load_more_button)
            
            # Esperar até que novos imóveis sejam carregados
            WebDriverWait(driver, 30).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "article.imovel.galeria-imoveis-thumb")) > num_imoveis_antes
            )
        except Exception as e:
            print(f"Erro ao carregar mais imóveis: {e}")
            break

# Definir a quantidade de vezes que deseja clicar no botão de carregar mais imóveis
quantidade_cliques = 100  # Aumentar a quantidade de cliques
carregar_mais_imoveis(quantidade_cliques)

# Esperar um pouco mais para garantir que todos os imóveis sejam carregados
time.sleep(10)

# Extrair informações básicas dos imóveis
soup = BeautifulSoup(driver.page_source, 'html.parser')
imoveis = soup.find_all('article', class_='imovel galeria-imoveis-thumb')

# Lista para armazenar os dados
data = []

# Função para extrair texto ou retornar None
def get_text_or_none(element):
    return element.text.strip() if element else None

# Função para extrair informações básicas de composição
def extrair_informacoes_composicao(composicao):
    # Utilizando regex para extrair as informações
    area_match = re.search(r'([\d\.]+)\s*m', composicao)
    quartos_match = re.search(r'(\d+)\s*Quarto', composicao)
    suite_match = re.search(r'\((\d+)\s*Suite', composicao)
    banheiros_match = re.search(r'(\d+)\s*Banheiro', composicao)
    lavabo_match = re.search(r'(\d+)\s*Lavabo', composicao)
    vagas_match = re.search(r'(\d+)\s*Vaga', composicao)

    # Capturando os valores ou definindo como '0' se não forem encontrados
    area = area_match.group(1) if area_match else '0'
    quartos = quartos_match.group(1) if quartos_match else '0'
    suite = suite_match.group(1) if suite_match else '0'
    banheiros = banheiros_match.group(1) if banheiros_match else '0'
    lavabo = lavabo_match.group(1) if lavabo_match else '0'
    vagas = vagas_match.group(1) if vagas_match else '0'

    return area, quartos, suite, banheiros, lavabo, vagas

# Função para limpar e converter preço para número
def limpar_preco(preco):
    preco_limpo = re.sub(r'[^\d]', '', preco)
    return float(preco_limpo) if preco_limpo else None

# Função para dividir a string do bairro em RU e bairro
def extrair_ru_e_bairro(texto):
    match = re.search(r'RU:\s*(\d+)\s*-\s*(.+)', texto)
    if (match):
        ru = match.group(1)
        bairro = match.group(2)
        return ru, bairro
    return '0', None

# Iterar sobre cada imóvel e extrair as informações básicas
for imovel in tqdm(imoveis, desc="Extraindo informações dos imóveis"):
    try:
        link_tag = imovel.find('p', class_='pull-left').a
        link = link_tag['href'] if link_tag else None
        titulo = get_text_or_none(link_tag)
        preco = get_text_or_none(imovel.find('p', class_='pull-right preco-imovel'))
        composicao_text = get_text_or_none(imovel.find('p', class_='composicao'))
        bairro_info = get_text_or_none(imovel.find_all('p')[-1])  # Última tag <p> do elemento
        
        if not preco:
            raise ValueError("Preço não encontrado")

        area, quartos, suite, banheiros, lavabo, vagas = extrair_informacoes_composicao(composicao_text)
        preco_num = limpar_preco(preco)
        area_num = float(area.replace(',', '.')) if area else 0
        ru, bairro = extrair_ru_e_bairro(bairro_info)

        # Verificar se o preço e a área são válidos
        if preco_num is not None and area_num > 0:
            data.append({
                'Título': titulo,
                'Link': link,
                'Preço': preco_num,
                'Área': area_num,
                'Quartos': int(quartos) if quartos else 0,
                'Suíte': int(suite) if suite else 0,
                'Banheiros': int(banheiros) if banheiros else 0,
                'Lavabo': int(lavabo) if lavabo else 0,
                'Vagas': int(vagas) if vagas else 0,
                'Bairro': bairro,
                'RU': int(ru),
                'M2': preco_num / area_num if area_num != 0 else 0
            })
    except Exception as e:
        print(f"Erro ao processar o imóvel: {e}")

# Fechar o navegador
driver.quit()

# Criar o DataFrame
df = pd.DataFrame(data)

# Salvar em um arquivo Excel
df.to_excel('imoveis.xlsx', index=False)

print("Dados salvos com sucesso!")
