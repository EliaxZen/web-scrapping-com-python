import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
)
import logging
from tqdm import tqdm
import re
import time
import random
import argparse

# Configurando o logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def configurar_driver():
    """Configura e retorna uma instância do WebDriver."""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)


def aceitar_cookies(driver):
    """Aceita cookies se o botão estiver presente."""
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "cookie-notifier-cta"))
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
    return re.sub(r"\D", "", dado)


def extrair_dados(driver):
    """Extrai dados de imóveis da página atual."""
    imoveis = driver.find_elements(By.CLASS_NAME, "property-card__content")
    dados = []
    for imovel in imoveis:
        try:
            titulo = tratar_dado(imovel, "property-card__title")
            endereco = tratar_dado(imovel, "property-card__address")
            preco = limpar_dado(tratar_dado(imovel, "property-card__price"))
            area = tratar_dado(imovel, "property-card__detail-area")
            area = limpar_dado(area) if "-" not in area else "N/A"
            quartos = limpar_dado(tratar_dado(imovel, "property-card__detail-room"))
            banheiros = limpar_dado(
                tratar_dado(imovel, "property-card__detail-bathroom")
            )
            vagas = limpar_dado(tratar_dado(imovel, "property-card__detail-garage"))

            dados.append([titulo, endereco, preco, area, quartos, banheiros, vagas])
        except Exception as e:
            logger.error(f"Erro ao processar imóvel: {e}")
    return dados


def carregar_pagina(driver, url):
    """Carrega uma página e tenta resolver qualquer problema de carregamento."""
    max_retentativas = 3
    for tentativa in range(max_retentativas):
        try:
            driver.get(url)
            return True
        except Exception as e:
            logger.warning(
                f"Erro ao carregar a página (tentativa {tentativa + 1}/{max_retentativas}): {e}"
            )
            time.sleep(random.uniform(1, 2))
    logger.error("Falha ao carregar a página após múltiplas tentativas.")
    return False


def rolar_ate_o_fim(driver):
    """Rola a página até o final para carregar todos os elementos."""
    altura_inicial = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        nova_altura = driver.execute_script("return document.body.scrollHeight")
        if nova_altura == altura_inicial:
            break
        altura_inicial = nova_altura


def clicar_nas_paginas(driver, pagina):
    """Clica no botão da página específica."""
    try:
        botao_pagina = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, f"button.js-change-page[data-page='{pagina}']")
            )
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", botao_pagina)
        driver.execute_script("arguments[0].click();", botao_pagina)
        time.sleep(1.5)
        return True
    except (
        TimeoutException,
        NoSuchElementException,
        ElementClickInterceptedException,
    ) as e:
        logger.error(f"Erro ao clicar no botão para a página {pagina}: {e}")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao clicar no botão para a página {pagina}: {e}")
        return False


def processar_pagina(driver):
    """Processa uma única página e retorna os dados extraídos."""
    rolar_ate_o_fim(driver)
    return extrair_dados(driver)


def main(num_paginas, max_imoveis):
    driver = configurar_driver()
    url = "https://www.vivareal.com.br/venda/distrito-federal/brasilia/"
    if not carregar_pagina(driver, url):
        return

    aceitar_cookies(driver)

    dados_imoveis = []
    pbar = tqdm(total=num_paginas, desc="Progresso")

    try:
        for pagina_atual in range(1, num_paginas + 1):
            if clicar_nas_paginas(driver, pagina_atual):
                dados_pagina = processar_pagina(driver)
                dados_imoveis.extend(dados_pagina)
                pbar.update(1)

                if len(dados_imoveis) >= max_imoveis:
                    logger.info(f"Limite de {max_imoveis} imóveis atingido.")
                    break

                time.sleep(random.uniform(0.5, 1))
            else:
                logger.info(f"Fim da navegação, página {pagina_atual} não acessível.")
                break

    except Exception as e:
        logger.error(f"Erro durante a execução: {e}")
    finally:
        pbar.close()
        driver.quit()

    dados_imoveis = dados_imoveis[:max_imoveis]

    colunas = ["Título", "Endereço", "Preço", "Área", "Quartos", "Banheiros", "Vagas"]
    df = pd.DataFrame(dados_imoveis, columns=colunas)

    for coluna in ["Preço", "Área", "Quartos", "Banheiros", "Vagas"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0)

    df = df[(df["Preço"] > 0) & (df["Área"] > 0)]
    df["M2"] = df["Preço"] / df["Área"]

    csv_filename = "imoveis.csv"
    df.to_csv(csv_filename, index=False, encoding="utf-8")
    logger.info(f"Dados salvos em {csv_filename}")

    excel_filename = "vivareal_DF.xlsx"
    df.to_excel(excel_filename, index=False)
    logger.info(f"Dados convertidos para Excel e salvos em {excel_filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Raspagem de dados de imóveis.")
    parser.add_argument(
        "--paginas",
        type=int,
        default=750,
        help="Número de páginas a serem processadas",
    )
    parser.add_argument(
        "--max_imoveis",
        type=int,
        default=26624,
        help="Número máximo de imóveis a serem coletados",
    )
    args = parser.parse_args()
    main(args.paginas, args.max_imoveis)
