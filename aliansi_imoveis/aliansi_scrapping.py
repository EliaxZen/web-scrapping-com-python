import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm
import re
import logging

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Função para inicializar o driver do Selenium
def inicializar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Rodar em modo headless para melhor performance
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()
    return driver

# Função para extrair detalhes de um imóvel
def extrair_detalhes_imovel(cartao):
    try:
        link = cartao.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
    except Exception as e:
        logging.error(f"Erro ao extrair link: {e}")
        link = None
    
    try:
        titulo = cartao.find_element(By.CSS_SELECTOR, ".titulo .h5").text
    except Exception as e:
        logging.error(f"Erro ao extrair título: {e}")
        titulo = None

    try:
        subtitulo = cartao.find_element(By.CSS_SELECTOR, ".titulo .font-weight-bold").text
    except Exception as e:
        logging.error(f"Erro ao extrair subtítulo: {e}")
        subtitulo = None

    try:
        preco = cartao.find_element(By.CSS_SELECTOR, ".valor .font-weight-bold").text
    except Exception as e:
        logging.error(f"Erro ao extrair preço: {e}")
        preco = None

    try:
        taxa_condominio = cartao.find_elements(By.CSS_SELECTOR, ".valor .font-weight-bold")[1].text
    except Exception as e:
        logging.error(f"Erro ao extrair taxa de condomínio: {e}")
        taxa_condominio = None

    try:
        dormitorios = next((e.find_element(By.TAG_NAME, "span").text.split()[0] for e in cartao.find_elements(By.CSS_SELECTOR, ".infra .tt") if "dorm" in e.text.lower()), None)
    except Exception as e:
        logging.error(f"Erro ao extrair dormitórios: {e}")
        dormitorios = None

    try:
        suites = next((e.find_element(By.TAG_NAME, "span").text.split()[0] for e in cartao.find_elements(By.CSS_SELECTOR, ".infra .tt") if "suíte" in e.text.lower() or "suite" in e.text.lower()), None)
    except Exception as e:
        logging.error(f"Erro ao extrair suítes: {e}")
        suites = None

    try:
        vagas = next((e.find_element(By.TAG_NAME, "span").text.split()[0] for e in cartao.find_elements(By.CSS_SELECTOR, ".infra .tt") if "vaga" in e.text.lower()), None)
    except Exception as e:
        logging.error(f"Erro ao extrair vagas: {e}")
        vagas = None

    try:
        area = next((e.find_element(By.TAG_NAME, "span").text.split()[0] for e in cartao.find_elements(By.CSS_SELECTOR, ".infra .tt") if "m²" in e.text.lower()), None)
    except Exception as e:
        logging.error(f"Erro ao extrair área: {e}")
        area = None

    return {
        "Link": link,
        "Título": titulo,
        "Subtítulo": subtitulo,
        "Preço": preco,
        "Taxa Condomínio": taxa_condominio,
        "Dormitórios": dormitorios,
        "Suítes": suites,
        "Vagas": vagas,
        "Área": area
    }

# Função para raspar dados do site AlianSi
def raspar_aliansi(paginas_para_raspar=5):
    driver = inicializar_driver()
    imoveis = []

    for pagina in tqdm(range(1, paginas_para_raspar + 1), desc="Raspando Páginas"):
        url = f"https://www.aliansi.com.br/imoveis?pg={pagina}&busca=venda&finalidade=venda&cidade="
        driver.get(url)
        
        # Scroll down to the bottom of the page to load all properties
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for the page to load
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        wait = WebDriverWait(driver, 10)
        cartoes = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card-imovel")))

        for cartao in cartoes:
            detalhes_imovel = extrair_detalhes_imovel(cartao)
            if detalhes_imovel:
                imoveis.append(detalhes_imovel)

    driver.quit()
    return imoveis

# Função para limpar colunas numéricas e preencher valores nulos com 0
def limpar_colunas_numericas(df, colunas):
    for coluna in colunas:
        df[coluna] = df[coluna].apply(lambda x: re.sub(r'\D', '', x) if pd.notnull(x) else x)
        df[coluna] = pd.to_numeric(df[coluna], errors='coerce').fillna(0)
    return df

# Função para filtrar imóveis inválidos
def filtrar_imoveis_invalidos(df, colunas_numericas):
    for coluna in colunas_numericas:
        df = df[df[coluna] > 0]
    return df

# Função principal
def main(paginas_para_raspar):
    imoveis = raspar_aliansi(paginas_para_raspar)
    df = pd.DataFrame(imoveis)
    
    colunas_numericas = ['Preço', 'Taxa Condomínio', 'Dormitórios', 'Suítes', 'Vagas', 'Área']
    df = limpar_colunas_numericas(df, colunas_numericas)
    df = filtrar_imoveis_invalidos(df, ['Preço', 'Área'])
    
    df.to_excel('imoveis_aliansi.xlsx', index=False)
    logging.info("Dados salvos em imoveis_aliansi.xlsx")

if __name__ == "__main__":
    paginas_para_raspar = int(input("Quantas páginas deseja iterar? "))
    main(paginas_para_raspar)
