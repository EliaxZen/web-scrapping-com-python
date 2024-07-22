import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from tqdm import tqdm
import logging

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def configurar_driver():
    opcoes = webdriver.ChromeOptions()
    opcoes.add_argument('--headless')
    opcoes.add_argument('--disable-gpu')
    opcoes.add_argument('--no-sandbox')
    opcoes.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opcoes)
    return driver

def aceitar_cookies(driver):
    try:
        botao_cookies = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "closeCookie"))
        )
        botao_cookies.click()
    except (NoSuchElementException, TimeoutException):
        pass

def extrair_dados_imovel(elemento_imovel):
    try:
        link = elemento_imovel.get_attribute("href")
        tipo = elemento_imovel.find_element(By.CSS_SELECTOR, ".card-with-buttons__title").text
        endereco = elemento_imovel.find_element(By.CSS_SELECTOR, ".card-with-buttons__heading").text

        partes_endereco = endereco.split(" - ")
        bairro, cidade, estado = partes_endereco if len(partes_endereco) == 3 else (None, None, None)

        lista_info = elemento_imovel.find_elements(By.CSS_SELECTOR, "ul > li")
        area = quartos = suites = banheiros = vagas = None
        for info in lista_info:
            texto = info.text.lower()
            if 'm²' in texto:
                area = re.search(r'\d+', texto)
                area = area.group() if area else 0
            elif 'quarto' in texto:
                quartos = re.search(r'\d+', texto)
                quartos = quartos.group() if quartos else 0
            elif 'suíte' in texto:
                suites = re.search(r'\d+', texto)
                suites = suites.group() if suites else 0
            elif 'banheiro' in texto:
                banheiros = re.search(r'\d+', texto)
                banheiros = banheiros.group() if banheiros else 0
            elif 'vaga' in texto:
                vagas = re.search(r'\d+', texto)
                vagas = vagas.group() if vagas else 0

        preco_elemento = elemento_imovel.find_element(By.CSS_SELECTOR, ".card-with-buttons__value")
        preco = re.search(r'\d+', preco_elemento.text.replace(".", "").replace(",", "."))
        preco = preco.group() if preco else 0

        return {
            "Link": link,
            "Tipo": tipo,
            "Bairro": bairro,
            "Cidade": cidade,
            "Estado": estado,
            "Área (m²)": area,
            "Quartos": quartos,
            "Suítes": suites,
            "Banheiros": banheiros,
            "Vagas": vagas,
            "Preço (R$)": preco
        }
    except (NoSuchElementException, TimeoutException, AttributeError, StaleElementReferenceException) as e:
        logging.error(f"Erro ao extrair dados do imóvel: {e}")
        return None

def clicar_ver_mais(driver):
    try:
        botao_ver_mais = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn.btn-md.btn-primary.btn-next"))
        )
        actions = ActionChains(driver)
        actions.move_to_element(botao_ver_mais).click().perform()
        time.sleep(1)
        return True
    except (NoSuchElementException, TimeoutException):
        return False

def carregar_todos_os_imoveis(driver):
    while True:
        if not clicar_ver_mais(driver):
            logging.info("Botão 'Ver mais' não encontrado ou não clicável. Carregamento completo.")
            break

def extrair_imoveis(driver, url):
    driver.get(url)
    aceitar_cookies(driver)
    
    carregar_todos_os_imoveis(driver)
    
    elementos_imoveis = driver.find_elements(By.CSS_SELECTOR, "a.card-with-buttons.borderHover")
    logging.info(f"Encontrados {len(elementos_imoveis)} elementos de imóveis na página.")
    
    imoveis = []
    for elemento_imovel in tqdm(elementos_imoveis, desc=f"Extraindo imóveis de {url}", unit="imóvel"):
        dados = extrair_dados_imovel(elemento_imovel)
        if dados:
            imoveis.append(dados)

    return imoveis

url = "https://www.valeimoveisto.com.br/imoveis/para-alugar"

driver = configurar_driver()

logging.info(f"Iniciando extração de imóveis de {url}.")
imoveis = extrair_imoveis(driver, url)
logging.info(f"Extração de imóveis concluída. Total extraído: {len(imoveis)}")

driver.quit()

df = pd.DataFrame(imoveis)

def tratar_dados(df):
    if df.empty:
        logging.warning("DataFrame está vazio.")
        return df

    df = df.fillna(0)  # Preenche valores NaN com 0
    cols_numericas = ["Área (m²)", "Quartos", "Suítes", "Banheiros", "Vagas", "Preço (R$)"]
    for col in cols_numericas:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # Remover imóveis com preço ou área igual a 0
    df = df[(df["Área (m²)"] > 0) & (df["Preço (R$)"] > 0)]
    
    return df

df = tratar_dados(df)

if not df.empty:
    df['M2'] = df.apply(lambda row: row['Preço (R$)'] / row['Área (m²)'] if row['Área (m²)'] > 0 else 0, axis=1)

df.to_excel("vale_imoveis_aluguel.xlsx", index=False)

logging.info("Processo concluído e dados salvos em 'vale_imoveis_venda.xlsx'.")
