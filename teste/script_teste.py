from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import re
import os

# Função para extrair conteúdo numérico de uma string
def extract_numeric(text):
    return re.sub(r'[^0-9,]', '', text)

# Função para extrair dados de uma única página
def extract_page_data(soup):
    properties = soup.find_all('div', class_='card mb-3 sombreado')
    data = []

    for prop in properties:
        try:
            item_edital = prop.find('h3', class_='card-title').get_text(strip=True).replace('Item : ', '').split('Edital : ')
            item = item_edital[0].strip()
            edital = item_edital[1].strip()

            details = prop.find('p', class_='card-text').get_text(separator='\n').split('\n')
            endereco = details[0].replace('Endereço: ', '').strip()
            regiao_adm = details[1].replace('Região Adm.: ', '').strip()
            numero_imoveis = int(details[2].replace('Número de Imóveis: ', '').strip())
            
            # Verificando se a string é vazia antes de converter para int
            area_text = details[3].replace('Área: ', '').replace(' m²', '').strip()
            area = int(extract_numeric(area_text)) if area_text else 0
            
            # Verificando se a string é vazia antes de converter para float
            preco_text = details[4].replace('Valor do Item: ', '').replace('R$', '').replace('.', '').replace(',', '.').strip()
            preco = float(extract_numeric(preco_text)) if preco_text else 0.0
            
            valor_caucao_text = details[5].replace('Valor da Caução: ', '').replace('R$', '').replace('.', '').replace(',', '.').strip()
            valor_caucao = float(extract_numeric(valor_caucao_text)) if valor_caucao_text else 0.0

            data.append({
                'Item': item,
                'Data Edital': edital,
                'Endereço': endereco,
                'Região Adm.': regiao_adm,
                'Número de Imóveis': numero_imoveis,
                'Área': area,
                'Preço': preco,
                'Valor da Caução': valor_caucao
            })
        except (IndexError, ValueError) as e:
            print(f"Erro ao processar um item: {e}")
            continue

    return data

# Função para extrair todos os dados navegando pelas páginas até a página limite
def extract_all_data(driver, base_url, max_pages):
    driver.get(base_url)
    all_data = []
    current_page = 0

    while True:
        current_page += 1
        try:
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, 'card mb-3 sombreado')))
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            all_data.extend(extract_page_data(soup))
        except Exception as e:
            print(f"Erro ao extrair dados da página {current_page}: {e}")
            break

        next_page = driver.find_elements(By.CSS_SELECTOR, 'ul.pagination.pagination-lg.sombreado li a')
        if len(next_page) > 1 and current_page < max_pages:
            try:
                next_page[-1].click()
                WebDriverWait(driver, 30).until(EC.staleness_of(next_page[-1]))  # Espera até que a página mude
            except Exception as e:
                print(f"Erro ao clicar na próxima página: {e}")
                break
        else:
            break

    return all_data

# Configuração do Selenium WebDriver
options = webdriver.ChromeOptions()
options.add_argument('--headless')

try:
    print("Instalando ChromeDriver...")

    chrome_driver_path = r"C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\teste\chromedriver.exe"
    service = ChromeService(executable_path=chrome_driver_path)

    driver = webdriver.Chrome(service=service, options=options)
    print("ChromeDriver instalado e driver inicializado.")

    base_url = 'https://comprasonline.terracap.df.gov.br/#'
    max_pages = 5

    data = extract_all_data(driver, base_url, max_pages)

    if data:
        df = pd.DataFrame(data)
        df['Preço'] = pd.to_numeric(df['Preço'], errors='coerce')
        df['Valor da Caução'] = pd.to_numeric(df['Valor da Caução'], errors='coerce')
        df = df.dropna(subset=['Preço'])
        df.fillna(0, inplace=True)

        df.to_excel('leiloes_imoveis_terracap.xlsx', index=False)
        print('Dados salvos em leiloes_imoveis_terracap.xlsx')
    else:
        print("Nenhum dado foi extraído.")

except Exception as e:
    print(f"Ocorreu um erro: {e}")

finally:
    try:
        if driver:
            driver.quit()
    except NameError:
        print("O driver não foi inicializado.")
