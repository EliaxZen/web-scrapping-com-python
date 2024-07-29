import csv
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException
import logging
from tqdm import tqdm
import re

# Configurando o logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def aceitar_cookies(driver):
    """Aceita cookies se o botão estiver presente."""
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'cookie-notifier-cta'))
        ).click()
        logger.info("Cookies aceitos.")
    except TimeoutException:
        logger.info("Botão de cookies não encontrado ou já aceito.")

def tratar_dado(imovel, class_name):
    """Tenta extrair e limpar o texto de um elemento, retorna 'N/A' se não encontrar."""
    try:
        dado = imovel.find_element(By.CLASS_NAME, class_name).text
        return re.sub(r'\D', '', dado) if 'price' in class_name else dado
    except NoSuchElementException:
        return "N/A"

def extrair_tipo(titulo):
    """Extrai o tipo do imóvel com base no título."""
    if not titulo:
        return "OUTROS"
    titulo = titulo.lower()
    if "apartamento" in titulo:
        return "Apartamento"
    elif "casa" in titulo:
        return "Casa"
    elif "casa-condominio" in titulo:
        return "Casa Condomínio"
    elif "galpao" in titulo:
        return "Galpão"
    elif "garagem" in titulo:
        return "Garagem"
    elif "hotel-flat" in titulo or "flat" in titulo:
        return "Flat"
    elif "kitnet" in titulo:
        return "Kitnet"
    elif "loja" in titulo:
        return "Loja"
    elif "loteamento" in titulo:
        return "Loteamento"
    elif "lote-terreno" in titulo:
        return "Lote Terreno"
    elif "ponto-comercial" in titulo:
        return "Ponto Comercial"
    elif "prédio" in titulo or "predio" in titulo:
        return "Prédio"
    elif "sala" in titulo:
        return "Sala"
    elif "rural" in titulo:
        return "Zona Rural"
    elif "lancamento" in titulo:
        return "Lançamento"
    else:
        return "OUTROS"

# Configurando o WebDriver Manager para gerenciar o ChromeDriver
options = Options()
options.add_argument("--headless")  # Executar em modo headless
options.add_argument("--disable-gpu")  # Desativar GPU
options.add_argument("--no-sandbox")  # Necessário para algumas configurações do sistema
options.add_argument("--disable-dev-shm-usage")  # Prevenir problemas de armazenamento
options.add_argument("--log-level=3")  # Desabilitar logs

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# URL inicial do site
url = "https://www.vivareal.com.br/venda/sp/sao-paulo/"
driver.get(url)

# Aceitar cookies se necessário
aceitar_cookies(driver)

# Criando uma lista para armazenar os dados
dados_imoveis = []

# Variável para decidir até qual página seguir
num_paginas = 41800  # Pode alterar esse valor conforme necessário

# Configurar a barra de progresso
pbar = tqdm(total=num_paginas, desc="Progresso")

pagina_atual = 1

while pagina_atual <= num_paginas:
    # Encontrar os elementos que contêm as informações dos imóveis
    imoveis = driver.find_elements(By.CLASS_NAME, 'property-card__content')

    # Iterar pelos imóveis e extrair as informações desejadas
    for imovel in imoveis:
        titulo = tratar_dado(imovel, 'property-card__title')
        endereco = tratar_dado(imovel, 'property-card__address')
        preco = tratar_dado(imovel, 'property-card__price')
        area = tratar_dado(imovel, 'property-card__detail-area')
        quartos = tratar_dado(imovel, 'property-card__detail-room')
        banheiros = tratar_dado(imovel, 'property-card__detail-bathroom')
        vagas = tratar_dado(imovel, 'property-card__detail-garage')

        # Determinar o tipo de imóvel
        tipo = extrair_tipo(titulo)

        # Adicionando os dados do imóvel na lista
        dados_imoveis.append([titulo, tipo, endereco, preco, area, quartos, banheiros, vagas])

    # Tentar encontrar o botão "Próxima página" para ir para a próxima página
    try:
        botao_proxima = driver.find_element(By.XPATH, '//button[contains(@class, "js-change-page") and contains(text(), "Próxima página")]')
        driver.execute_script("arguments[0].scrollIntoView(true);", botao_proxima)
        botao_proxima.click()
        
        # Esperar a URL mudar para a próxima página
        WebDriverWait(driver, 10).until(
            EC.url_contains(f"?pagina={pagina_atual + 1}")
        )
        
        pagina_atual += 1
        pbar.update(1)  # Atualizar a barra de progresso
    except ElementClickInterceptedException:
        try:
            # Tentando fechar a mensagem de cookie
            botao_cookies = driver.find_element(By.XPATH, '//button[contains(@class, "cookie-notifier__button")]')
            botao_cookies.click()
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "js-change-page") and contains(text(), "Próxima página")]'))
            ).click()
            pagina_atual += 1
            pbar.update(1)  # Atualizar a barra de progresso
        except NoSuchElementException:
            logger.warning("Não foi possível encontrar o botão de cookies.")
    except NoSuchElementException:
        logger.info("Todas as páginas foram processadas.")
        break
    except TimeoutException:
        logger.warning("A próxima página não carregou a tempo.")
        break

# Fechar a barra de progresso
pbar.close()

# Fechar o navegador
driver.quit()

# Definindo o nome das colunas
colunas = ['Título', 'Tipo', 'Endereço', 'Preço', 'Área', 'Quartos', 'Banheiros', 'Vagas']

# Convertendo os dados para um DataFrame
df = pd.DataFrame(dados_imoveis, columns=colunas)

# Convertendo colunas para numéricas e preenchendo valores ausentes com 0
df['Preço'] = pd.to_numeric(df['Preço'], errors='coerce').fillna(0)
df['Área'] = pd.to_numeric(df['Área'], errors='coerce').fillna(0)
df['Quartos'] = pd.to_numeric(df['Quartos'], errors='coerce').fillna(0)
df['Banheiros'] = pd.to_numeric(df['Banheiros'], errors='coerce').fillna(0)
df['Vagas'] = pd.to_numeric(df['Vagas'], errors='coerce').fillna(0)

# Excluir imóveis com preço ou área igual a 0
df = df[(df['Preço'] > 0) & (df['Área'] > 0)]

# Criar a coluna M2
df['M2'] = df['Preço'] / df['Área']

# Salvando os dados em um arquivo CSV
csv_filename = 'imoveis.csv'
df.to_csv(csv_filename, index=False, encoding='utf-8')

logger.info(f"Dados salvos em {csv_filename}")

# Convertendo o arquivo CSV para Excel
excel_filename = 'imoveis.xlsx'
df.to_excel(excel_filename, index=False)

logger.info(f"Dados convertidos para Excel e salvos em {excel_filename}")
