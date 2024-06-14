import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuração do WebDriver
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Executar em modo headless (sem abrir a janela do navegador)
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# Instalar e inicializar o WebDriver usando o webdriver-manager
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# URL da página principal
url = "https://refugiosurbanos.com.br/imoveis/"
driver.get(url)

# Função para carregar todos os imóveis clicando no botão "Carregar mais imóveis"
def load_all_properties():
    while True:
        try:
            load_more_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div#paginador a[data-page]"))
            )
            load_more_button.click()
            time.sleep(2)  # Esperar para carregar os novos imóveis
        except Exception as e:
            print("Todos os imóveis foram carregados ou ocorreu um erro:", e)
            break

# Função para extrair informações detalhadas de cada imóvel
def extract_property_details(link):
    driver.get(link)
    details = {}
    
    try:
        details['title'] = driver.find_element(By.CSS_SELECTOR, "h1.titulo_pagina.no-border").text
    except:
        details['title'] = None
    
    try:
        details['description'] = driver.find_element(By.CSS_SELECTOR, "article#descricao_imovel").text
    except:
        details['description'] = None
    
    try:
        details['bairro'] = driver.find_element(By.XPATH, "//article[@id='detalhes_imovel']//h2[text()='Bairro']/following-sibling::p").text
    except:
        details['bairro'] = None
    
    try:
        details['area_util'] = driver.find_element(By.XPATH, "//article[@id='detalhes_imovel']//h2[text()='Configuração']/following-sibling::p[1]").text.split("\n")[0]
    except:
        details['area_util'] = None
    
    try:
        details['configuracao'] = driver.find_element(By.XPATH, "//article[@id='detalhes_imovel']//h2[text()='Configuração']/following-sibling::p[1]").text
    except:
        details['configuracao'] = None
    
    try:
        details['detalhes'] = driver.find_element(By.XPATH, "//article[@id='detalhes_imovel']//h2[text()='Detalhes']/following-sibling::p").text
    except:
        details['detalhes'] = None
    
    try:
        details['valores'] = driver.find_element(By.XPATH, "//article[@id='detalhes_imovel']//h2[text()='Valores']/following-sibling::p").text
    except:
        details['valores'] = None
    
    try:
        details['codigo_ru'] = driver.find_element(By.XPATH, "//article[@id='detalhes_imovel']//h2[text()='Código RU']/following-sibling::p").text
    except:
        details['codigo_ru'] = None
    
    return details

# Carregar todos os imóveis
load_all_properties()

# Obter todos os links dos imóveis
property_links = [element.get_attribute('href') for element in driver.find_elements(By.CSS_SELECTOR, "article.imovel a[target='_blank']")]

# Extrair informações detalhadas de cada imóvel
properties = []
for link in property_links:
    properties.append(extract_property_details(link))
    time.sleep(1)  # Espera para evitar sobrecarga do servidor

# Encerrar o driver
driver.quit()

# Exibir as informações extraídas
for property in properties:
    print(property)
