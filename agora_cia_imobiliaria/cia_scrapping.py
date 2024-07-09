from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import re
from bs4 import BeautifulSoup
from tqdm import tqdm

# Configuração do WebDriver
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Para rodar o navegador em modo headless (sem interface gráfica)
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Função para limpar e converter valores numéricos
def clean_numeric(value):
    return float(re.sub(r'[^\d]', '', value)) if value else 0

# Variável para definir o número de páginas a serem iteradas
num_pages = 119  # Defina o número de páginas que deseja iterar

# URL base e inicialização de variáveis
base_url = "https://www.agora.imb.br/venda/busca?property_type=vendas&order=&category=&price=&property_code=&dormitories=&garages=&page={}"
property_data = []

# Loop para iterar sobre as páginas
for page_number in range(1, num_pages + 1):
    # Acessa a página
    driver.get(base_url.format(page_number))
    time.sleep(3)

    # Desce a página até o final para carregar todos os imóveis
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # Obtém o HTML da página
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Seleção de todos os imóveis na página
    properties = soup.find_all('div', class_='card shadow-hover-5 bg-white shadow-lg-4 zoomIn animated')

    # Verificação de imóveis na página
    if not properties:
        print(f"Página {page_number}: Nenhum imóvel encontrado.")
        break

    # Adiciona barra de progresso para imóveis
    for prop in tqdm(properties, desc=f'Processando página {page_number}'):
        try:
            # Extração de informações do imóvel
            link_tag = prop.find('h2', class_='card-title fs-16 lh-2 mb-0 text-center no-margin').find('a')
            if not link_tag:
                print("Tag de link não encontrada.")
                continue
            link = link_tag['href']
            print(f"Link: {link}")

            price_tag = prop.find('p', class_='fs-17 font-weight-bold text-heading mb-0')
            if not price_tag:
                print("Tag de preço não encontrada.")
                continue
            price = price_tag.text.strip()
            price = clean_numeric(price)
            print(f"Preço: {price}")

            # Requisição e parse do link do imóvel
            driver.get(link)
            time.sleep(3)
            prop_soup = BeautifulSoup(driver.page_source, 'html.parser')

            title_tag = prop_soup.find('h2', class_='fs-26 font-weight-600 lh-12 text-heading mb-0 d-flex align-items-center justify-content-center mb-2')
            title = title_tag.text.strip() if title_tag else None

            address_tag = prop_soup.find('p', class_='mb-0')
            address = address_tag.text.strip() if address_tag else None

            description_tag = prop_soup.find('p', class_='lh-214 ucfirst')
            description = description_tag.text.strip() if description_tag else None

            details = prop_soup.find_all('div', class_='col-6 col-lg-3 col-sm-4 mb-6')
            
            # Inicialização de variáveis do imóvel
            bedrooms = bathrooms = garages = area = property_type = 0

            # Extração de detalhes do imóvel
            for detail in details:
                label = detail.find('h5').text.strip().lower() if detail.find('h5') else None
                value = detail.find('p').text.strip() if detail.find('p') else '0'

                if label == 'quartos':
                    bedrooms = int(value) if value.isdigit() else 0
                elif label == 'banheiros':
                    bathrooms = int(value) if value.isdigit() else 0
                elif label == 'garagem':
                    garages = int(value) if value.isdigit() else 0
                elif label == 'área':
                    area = clean_numeric(value) if value else 0
                elif label == 'tipo':
                    property_type = value
            
            # Adiciona dados ao dicionário
            property_info = {
                'Link': link,
                'Preço': price,
                'Título': title,
                'Endereço': address,
                'Descrição': description,
                'Quartos': bedrooms,
                'Banheiros': bathrooms,
                'Garagens': garages,
                'Área': area,
                'Tipo': property_type,
            }
            print(f"Imóvel extraído: {property_info}")
            property_data.append(property_info)
        except Exception as e:
            print(f"Erro ao processar imóvel: {e}")
            time.sleep(1)

# Conversão para DataFrame
df = pd.DataFrame(property_data)

# Substituição de valores NaN por 0 em colunas numéricas
numeric_columns = ['Preço', 'Quartos', 'Banheiros', 'Garagens', 'Área']
df[numeric_columns] = df[numeric_columns].fillna(0)

# Salvamento em arquivo Excel
df.to_excel('imoveis_agora.xlsx', index=False)

print("Dados salvos em imoveis_agora.xlsx")
print(f"Número total de imóveis extraídos: {len(df)}")

# Fecha o driver
driver.quit()
