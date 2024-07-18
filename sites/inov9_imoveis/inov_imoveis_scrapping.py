import logging
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from tqdm import tqdm

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def configure_driver():
    """Configura o WebDriver do Chrome."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-extensions")
    options.add_argument("--ignore-certificate-errors")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def accept_cookies(driver):
    """Aceita os cookies da página."""
    try:
        cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-success[onclick='onCookieCloses()']"))
        )
        cookie_button.click()
        logging.info("Cookies aceitos.")
    except Exception as e:
        logging.error(f"Erro ao aceitar cookies: {e}")

def click_ver_mais(driver, times):
    """Clica no botão 'Ver mais' um número específico de vezes."""
    for _ in tqdm(range(times), desc="Clicando no botão 'Ver mais'"):
        try:
            ver_mais_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.pagination-cell button.btn-next"))
            )
            ver_mais_button.click()
            time.sleep(2)
            logging.info("Botão 'Ver mais' clicado.")
        except Exception as e:
            logging.error(f"Erro ao clicar no botão 'Ver mais': {e}")
            break

def extract_property_data(driver):
    """Extrai as informações dos imóveis listados na página."""
    properties = driver.find_elements(By.CSS_SELECTOR, "a.card-with-buttons.borderHover")
    logging.info(f"Número de imóveis encontrados: {len(properties)}")
    data = []
    
    for prop in tqdm(properties, desc="Extraindo dados dos imóveis"):
        try:
            link = f"https://www.inov9imoveis.com.br{prop.get_attribute('href')}"
            logging.info(f"Link: {link}")
        except Exception as e:
            link = ""
            logging.error(f"Erro ao extrair link: {e}")
        
        try:
            tipo = prop.find_element(By.CSS_SELECTOR, "p.card-with-buttons__title").text
            logging.info(f"Tipo: {tipo}")
        except Exception as e:
            tipo = ""
            logging.error(f"Erro ao extrair tipo: {e}")
        
        try:
            endereco = prop.find_element(By.CSS_SELECTOR, "h2.card-with-buttons__heading").text
            bairro, cidade, estado = endereco.split(" - ")
            logging.info(f"Endereço: {endereco}")
            logging.info(f"Bairro: {bairro}, Cidade: {cidade}, Estado: {estado}")
        except Exception as e:
            bairro, cidade, estado = "", "", ""
            logging.error(f"Erro ao extrair endereço: {e}")
        
        try:
            detalhes = prop.find_element(By.CSS_SELECTOR, "div.card-with-buttons__footer ul").find_elements(By.TAG_NAME, "li")
            area = re.sub(r'\D', '', detalhes[0].text) if len(detalhes) > 0 else "0"
            quartos = re.sub(r'\D', '', detalhes[1].text) if len(detalhes) > 1 else "0"
            suites = re.sub(r'\D', '', detalhes[2].text) if len(detalhes) > 2 else "0"
            banheiros = re.sub(r'\D', '', detalhes[3].text) if len(detalhes) > 3 else "0"
            vagas = re.sub(r'\D', '', detalhes[4].text) if len(detalhes) > 4 else "0"
            logging.info(f"Área: {area}, Quartos: {quartos}, Suítes: {suites}, Banheiros: {banheiros}, Vagas: {vagas}")
        except Exception as e:
            area, quartos, suites, banheiros, vagas = "0", "0", "0", "0", "0"
            logging.error(f"Erro ao extrair detalhes: {e}")
        
        try:
            preco = re.sub(r'\D', '', prop.find_element(By.CSS_SELECTOR, "div.card-with-buttons__value-container p.card-with-buttons__value").text)
            logging.info(f"Preço: {preco}")
        except Exception as e:
            preco = "0"
            logging.error(f"Erro ao extrair preço: {e}")
        
        # Garantir que os valores numéricos não sejam vazios
        area = int(area) if area.isdigit() else 0
        quartos = int(quartos) if quartos.isdigit() else 0
        suites = int(suites) if suites.isdigit() else 0
        banheiros = int(banheiros) if banheiros.isdigit() else 0
        vagas = int(vagas) if vagas.isdigit() else 0
        preco = int(preco) if preco.isdigit() else 0
        
        data.append({
            "Link": link,
            "Tipo": tipo,
            "Bairro": bairro,
            "Cidade": cidade,
            "Estado": estado,
            "Área": area,
            "Quartos": quartos,
            "Suítes": suites,
            "Banheiros": banheiros,
            "Vagas": vagas,
            "Preço": preco
        })
    
    return data

def main(url, ver_mais_clicks):
    driver = configure_driver()
    
    try:
        driver.get(url)
        accept_cookies(driver)
        click_ver_mais(driver, ver_mais_clicks)
        property_data = extract_property_data(driver)
    finally:
        driver.quit()
    
    # Criar DataFrame
    df = pd.DataFrame(property_data)
    
    # Remover imóveis com preço ou área inválidos
    df = df[(df["Preço"] > 0) & (df["Área"] > 0)]
    
    # Adicionar coluna M2
    df["M2"] = df["Preço"] / df["Área"]
    
    # Verificar se o DataFrame está vazio
    if df.empty:
        logging.warning("Nenhum dado foi extraído.")
    else:
        # Salvar em arquivo Excel
        df.to_excel("imoveis_inov9.xlsx", index=False)
        logging.info("Dados salvos com sucesso em imoveis_inov9.xlsx")

if __name__ == "__main__":
    URL = "https://www.inov9imoveis.com.br/imoveis/a-venda"
    VER_MAIS_CLICKS = 1000
    main(URL, VER_MAIS_CLICKS)
