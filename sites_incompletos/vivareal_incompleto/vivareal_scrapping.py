import csv
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException
import logging
from tqdm import tqdm
import re
import time
import argparse

# Configurando o logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def configurar_driver():
    """Configura e retorna uma instância do WebDriver."""
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service)

def aceitar_cookies(driver):
    """Aceita cookies se o botão estiver presente."""
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'cookie-notifier-cta'))
        ).click()
        logger.info("Cookies aceitos.")
    except TimeoutException:
        logger.info("Botão de cookies não encontrado ou já aceito.")
    except Exception as e:
        logger.error(f"Erro ao tentar aceitar cookies: {e}")

def tratar_dado(elemento, class_name):
    """Tenta extrair o texto de um elemento, retorna 'N/A' se não encontrar."""
    try:
        return elemento.find_element(By.CLASS_NAME, class_name).text
    except NoSuchElementException:
        return "N/A"
    except Exception as e:
        logger.error(f"Erro ao tratar dado: {e}")
        return "N/A"

def limpar_dado(dado):
    """Remove todos os caracteres não numéricos de um dado."""
    return re.sub(r'\D', '', dado)

def extrair_dados(driver):
    """Extrai dados de imóveis da página atual."""
    imoveis = driver.find_elements(By.CLASS_NAME, 'property-card__content')
    dados = []

    for imovel in imoveis:
        titulo = tratar_dado(imovel, 'property-card__title')
        endereco = tratar_dado(imovel, 'property-card__address')
        preco = tratar_dado(imovel, 'property-card__price')
        area = tratar_dado(imovel, 'property-card__detail-area')
        quartos = tratar_dado(imovel, 'property-card__detail-room')
        banheiros = tratar_dado(imovel, 'property-card__detail-bathroom')
        vagas = tratar_dado(imovel, 'property-card__detail-garage')

        # Limpar e converter os dados numéricos
        preco = limpar_dado(preco)
        area = limpar_dado(area) if '-' not in area else "N/A"
        quartos = limpar_dado(quartos)
        banheiros = limpar_dado(banheiros)
        vagas = limpar_dado(vagas)

        dados.append([titulo, endereco, preco, area, quartos, banheiros, vagas])

    return dados

def navegar_para_proxima_pagina(driver):
    """Navega para a próxima página de resultados."""
    try:
        botao_proxima = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "js-change-page") and contains(text(), "Próxima página")]'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", botao_proxima)
        botao_proxima.click()
        return True
    except (ElementClickInterceptedException, TimeoutException):
        logger.warning("Problema ao clicar no botão de próxima página.")
        return False
    except NoSuchElementException:
        logger.info("Botão de próxima página não encontrado.")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao navegar para a próxima página: {e}")
        return False

def main(num_paginas):
    driver = configurar_driver()
    url = "https://www.vivareal.com.br/venda/sp/sao-paulo/"
    driver.get(url)

    aceitar_cookies(driver)

    dados_imoveis = []
    pbar = tqdm(total=num_paginas, desc="Progresso")

    try:
        for pagina_atual in range(1, num_paginas + 1):
            dados_imoveis.extend(extrair_dados(driver))
            
            if not navegar_para_proxima_pagina(driver):
                logger.info("Todas as páginas foram processadas ou não foi possível carregar a próxima página.")
                break
            
            pbar.update(1)
            time.sleep(2)  # Intervalo para evitar sobrecarga no servidor

    except Exception as e:
        logger.error(f"Erro durante a execução: {e}")
    finally:
        pbar.close()
        driver.quit()

    colunas = ['Título', 'Endereço', 'Preço', 'Área', 'Quartos', 'Banheiros', 'Vagas']
    df = pd.DataFrame(dados_imoveis, columns=colunas)
    df['Preço'] = pd.to_numeric(df['Preço'], errors='coerce').fillna(0)
    df['Área'] = pd.to_numeric(df['Área'], errors='coerce').fillna(0)
    df['Quartos'] = pd.to_numeric(df['Quartos'], errors='coerce').fillna(0)
    df['Banheiros'] = pd.to_numeric(df['Banheiros'], errors='coerce').fillna(0)
    df['Vagas'] = pd.to_numeric(df['Vagas'], errors='coerce').fillna(0)
    df = df[(df['Preço'] > 0) & (df['Área'] > 0)]
    df['M2'] = df['Preço'] / df['Área']

    csv_filename = 'imoveis.csv'
    df.to_csv(csv_filename, index=False, encoding='utf-8')
    logger.info(f"Dados salvos em {csv_filename}")

    excel_filename = 'imoveis.xlsx'
    df.to_excel(excel_filename, index=False)
    logger.info(f"Dados convertidos para Excel e salvos em {excel_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Raspagem de dados de imóveis.")
    parser.add_argument('--paginas', type=int, default=41800, help="Número de páginas a serem processadas")
    args = parser.parse_args()
    main(args.paginas)
