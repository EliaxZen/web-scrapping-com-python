from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import random
import requests

# Lista de agentes de usuário
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
]

# Lista de proxies (adicione seus proxies aqui)
proxy_list = [
    'http://proxy1.example.com:8080',
    'http://proxy2.example.com:8080',
    # Adicione mais proxies conforme necessário
]

# Função para verificar se o proxy está funcionando
def verificar_proxy(proxy):
    url = 'http://www.google.com'
    proxies = {
        'http': proxy,
        'https': proxy,
    }
    try:
        response = requests.get(url, proxies=proxies, timeout=5)
        if response.status_code == 200:
            return True
    except Exception as e:
        print(f"Proxy {proxy} falhou: {e}")
    return False

# Escolher um proxy funcional
proxy = None
for p in proxy_list:
    if verificar_proxy(p):
        proxy = p
        break

if proxy is None:
    print("Nenhum proxy funcional encontrado. Por favor, atualize a lista de proxies.")
    exit()

# Configurar o driver do Selenium
service = ChromeService(executable_path=ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Executar em modo headless
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-blink-features=AutomationControlled')  # Desabilitar controle de automação do Blink
options.add_argument(f'user-agent={random.choice(user_agents)}')
options.add_argument(f'--proxy-server={proxy}')  # Adicionar proxy funcional

# Evitar detecção como bot
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(service=service, options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

# URL inicial
url = 'https://www.remax.com.br/PublicListingList.aspx#mode=gallery&tt=261&cur=BRL&sb=MostRecent&page=1&sc=55&pm=9523&lsgeo=0,9523,0,0&sid=ba6197c6-fb1d-43a8-898e-635b72029ea5'
driver.get(url)

lista_de_imoveis = []

# Definir o número de páginas para processar
num_paginas = 9

for pagina in range(1, num_paginas + 1):
    print(f'Processando página: {pagina}')
    
    try:
        # Esperar os imóveis carregarem
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'gallery-item-container'))
        )
        
        # Coletar os imóveis da página
        imoveis = driver.find_elements(By.CLASS_NAME, 'gallery-item-container')
        
        for imovel in imoveis:
            try:
                # Link do imóvel
                link_elem = imovel.find_element(By.CSS_SELECTOR, 'div.gallery-title a')
                link = 'https://www.remax.com.br' + link_elem.get_attribute('href')
                titulo = link_elem.get_attribute('title')
                
                # Preço do imóvel
                preco_elem = imovel.find_element(By.CSS_SELECTOR, 'span.gallery-price-main a.proplist_price')
                preco = preco_elem.text.strip() if preco_elem else None

                # Tipo do imóvel
                tipo_imovel_elem = imovel.find_element(By.CSS_SELECTOR, 'div.gallery-transtype span')
                tipo_imovel = tipo_imovel_elem.text.strip() if tipo_imovel_elem else None

                # Área, Dormitórios, Banheiros e Ambientes Totais
                area_elem = imovel.find_element(By.XPATH, ".//img[@src='/common/images/2019/Sq-meter.svg']/following-sibling::span[@class='gallery-attr-item-value']")
                area = area_elem.text.strip() if area_elem else None

                quartos_elem = imovel.find_element(By.XPATH, ".//img[@src='/common/images/2019/bedrooms.svg']/following-sibling::span[@class='gallery-attr-item-value']")
                quartos = quartos_elem.text.strip() if quartos_elem else None

                banheiros_elem = imovel.find_element(By.XPATH, ".//img[@src='/common/images/2019/bathrooms.svg']/following-sibling::span[@class='gallery-attr-item-value']")
                banheiros = banheiros_elem.text.strip() if banheiros_elem else None

                ambientes_totais_elem = imovel.find_element(By.XPATH, ".//img[@src='/common/images/2019/total-rooms.svg']/following-sibling::span[@class='gallery-attr-item-value']")
                ambientes_totais = ambientes_totais_elem.text.strip() if ambientes_totais_elem else None

                # Adicionando informações na lista de imóveis
                lista_de_imoveis.append([
                    titulo, link, preco, tipo_imovel, area, quartos, banheiros, ambientes_totais
                ])

            except Exception as e:
                print(f"Erro ao processar imóvel: {e}")

        # Clicar no botão para a próxima página
        next_button = driver.find_element(By.CSS_SELECTOR, f'a.ajax-page-link[data-page="{pagina + 1}"]')
        next_button.click()
        
        # Esperar um pouco para garantir que a próxima página foi carregada
        time.sleep(5)
        
    except Exception as e:
        print(f"Erro ao processar página {pagina}: {e}")
        break

# Fechar o navegador
driver.quit()

# Criar DataFrame
df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Link', 'Preço', 'Tipo Imóvel', 'Área', 'Quartos', 'Banheiros', 'Ambientes Totais'])

# Remover duplicatas com base na coluna 'Link'
df_imovel = df_imovel.drop_duplicates(subset='Link')

# Função para limpar e converter colunas numéricas
def limpar_conversao_numerica(coluna):
    return pd.to_numeric(coluna.str.replace(r'\D', '', regex=True), errors='coerce')

# Aplicar função de limpeza nas colunas numéricas
df_imovel['Preço'] = limpar_conversao_numerica(df_imovel['Preço'])
df_imovel['Área'] = limpar_conversao_numerica(df_imovel['Área'])
df_imovel['Quartos'] = limpar_conversao_numerica(df_imovel['Quartos'])
df_imovel['Banheiros'] = limpar_conversao_numerica(df_imovel['Banheiros'])
df_imovel['Ambientes Totais'] = limpar_conversao_numerica(df_imovel['Ambientes Totais'])

# Remover imóveis sem preço ou área
df_imovel = df_imovel.dropna(subset=['Preço', 'Área'])

# Adicionar coluna M2
df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Área']

# Exibir DataFrame final
print(df_imovel)

# Salvar DataFrame em um arquivo Excel
df_imovel.to_excel('remax_imoveis.xlsx', index=False)
print("Arquivo Excel salvo com sucesso.")
