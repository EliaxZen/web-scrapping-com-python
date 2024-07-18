import pandas as pd
import re
import logging
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração do Selenium com WebDriver Manager
options = Options()
options.add_argument("--headless")  # Executar em modo headless
options.add_argument("--disable-gpu")  # Desabilitar GPU
options.add_argument("--no-sandbox")  # Adicionar opções de segurança
options.add_argument("--disable-dev-shm-usage")  # Adicionar opções de segurança
service = Service(ChromeDriverManager().install())

# Função para configurar e criar um driver
def create_driver():
    return webdriver.Chrome(service=service, options=options)

driver = create_driver()
driver.implicitly_wait(10)  # Espera implícita

# Função para extrair e limpar informações de cada imóvel
def extrair_informacoes(imovel):
    try:
        # Extrair o link do imóvel
        link = imovel.find_element(By.XPATH, './ancestor::a').get_attribute('href')
        
        titulo = imovel.find_element(By.CLASS_NAME, "card-title").text.strip()
        
        endereco_codigo = imovel.find_element(By.CLASS_NAME, "container-endereco")
        endereco = endereco_codigo.find_element(By.CLASS_NAME, "card-text").text.strip()
        codigo = endereco_codigo.find_element(By.CLASS_NAME, "preco-cond-card").text.strip().replace("Código. ", "")
        
        preco_str = imovel.find_element(By.CLASS_NAME, "preco-imovel-card").text.strip().replace("R$", "").replace(".", "").replace(",", "").strip()
        if not preco_str:
            logging.warning(f"Imóvel sem preço encontrado: {titulo}")
            return None
        
        area_str = imovel.find_elements(By.CLASS_NAME, "container-icon")[0].text.strip()
        area = float(re.sub(r'[^\d.]', '', area_str.replace(" m²", ""))) if area_str else 0
        
        quartos_str = imovel.find_elements(By.CLASS_NAME, "container-icon")[1].text.strip()
        quartos = int(re.sub(r'[^\d]', '', quartos_str.replace(" quartos", ""))) if quartos_str else 0
        
        vagas_str = imovel.find_elements(By.CLASS_NAME, "container-icon")[2].text.strip()
        vagas = int(re.sub(r'[^\d]', '', vagas_str.replace(" vagas", ""))) if vagas_str else 0
        
        return {
            "Título": titulo,
            "Endereço": endereco,
            "Código": codigo,
            "Preço": preco_str,
            "Área (m²)": area,
            "Quartos": quartos,
            "Vagas": vagas,
            "Link": link
        }
    except NoSuchElementException as e:
        logging.error(f"Erro ao extrair informações de um imóvel: {e}")
        return None

# Função para realizar o scraping das páginas
def fazer_scraping(url_base, num_paginas):
    lista_imoveis = []

    driver.get(url_base)

    for page in tqdm(range(1, num_paginas + 1), desc="Scraping páginas", unit="página"):
        try:
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.ID, "container-resultado-busca")))
            time.sleep(2)
            
            container_resultado = driver.find_element(By.ID, "container-resultado-busca")
            imoveis = container_resultado.find_elements(By.CLASS_NAME, "card")
        except (NoSuchElementException, TimeoutException) as e:
            logging.warning(f"Nenhum imóvel encontrado ou houve um erro: {e}")
            driver.save_screenshot("erro_pagina.png")
            continue

        if not imoveis:
            logging.warning("Nenhum imóvel encontrado.")
            continue

        for imovel in imoveis:
            info_imovel = extrair_informacoes(imovel)
            if info_imovel:
                lista_imoveis.append(info_imovel)
            else:
                logging.warning("Imóvel não possui informações completas ou válidas.")

        try:
            # Encontra o botão da próxima página
            botao_proxima_pagina = driver.find_element(By.XPATH, f"//div[@class='container-paginacao']//div[@class='btn-paginacao'][span[text()='{page + 1}']]")
            botao_proxima_pagina.click()
            time.sleep(2)  # Tempo para garantir que a página carregue
        except NoSuchElementException:
            logging.warning("Botão de próxima página não encontrado. Finalizando scraping.")
            break

    logging.info(f"Total de imóveis extraídos: {len(lista_imoveis)}")
    return lista_imoveis

# URL base do site
url_base = "https://www.invisttanegocios.com.br/venda/?"

# Número de cliques no botão de próxima página (defina um valor adequado)
num_paginas = 38

# Realiza o scraping
dados_imoveis = fazer_scraping(url_base, num_paginas)

# Fechar o driver do Selenium
driver.quit()

# Verificar se dados foram extraídos
if not dados_imoveis:
    logging.info("Nenhum dado foi extraído.")
else:
    # Cria um DataFrame com os dados dos imóveis
    df = pd.DataFrame(dados_imoveis)

    # Mostrar as primeiras linhas do DataFrame para verificação
    logging.info("Dados extraídos:")
    logging.info(df.head())

    # Preencher valores vazios nas colunas numéricas com 0
    df.fillna({
        'Preço': 0,
        'Área (m²)': 0,
        'Quartos': 0,
        'Vagas': 0
    }, inplace=True)

    # Converter colunas numéricas para tipos apropriados
    df['Preço'] = pd.to_numeric(df["Preço"], errors='coerce')
    df['Área (m²)'] = pd.to_numeric(df["Área (m²)"], errors='coerce')
    df['Quartos'] = pd.to_numeric(df["Quartos"], errors='coerce')
    df['Vagas'] = pd.to_numeric(df["Vagas"], errors='coerce')
    df['Código'] = pd.to_numeric(df["Código"], errors='coerce')

    # Remove imóveis com preço igual a 0
    df = df[df['Preço'] > 0]
    df = df[df['Área (m²)'] > 0]

    # Criar a coluna M2 como resultado da divisão entre Preço e Área
    df['M2'] = df['Preço'] / df['Área (m²)']
    df['M2'] = df['M2'].fillna(0)  # Preencher valores vazios com 0

    # Mostrar as primeiras linhas do DataFrame para verificação após tratamento
    logging.info("Dados após tratamento:")
    logging.info(df.head())

    # Salva os dados em um arquivo Excel
    df.to_excel("invistta_imobiliaria_venda.xlsx", index=False)

    logging.info("Scraping concluído e dados salvos em invistta_imobiliaria_venda.xlsx")