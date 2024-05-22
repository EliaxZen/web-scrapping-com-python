import threading
from time import sleep


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from distrito_federal_setor import setores


# Configurações do Chrome
options = Options()

# Definir um user-agent para evitar a detecção de headless
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36")

# Desativar o uso do WebGL se não for necessário para o site
options.add_argument("--disable-webgl")


def extrair_setor(titulo):
    palavras = titulo.split()
    palavras_upper = [palavra.upper() for palavra in palavras]
    for palavra in palavras_upper:
        if palavra in setores:
            return palavra
    return "OUTRO"


def print_imoveis_carregados(driver):
    try:
        while True:
            sleep(5)
            imoveis_carregados = len(
                driver.find_elements(
                    By.XPATH, "/html/body/div[1]/div/div/main/section[2]/div/div[2]/div[2]/div/a"
                )
            )
            print(f"Imóveis carregados: {imoveis_carregados}")
    except KeyboardInterrupt:
        pass


def scrape_imoveis():
    opts = Options()
    #opts.add_argument("--headless")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--memory-growth=10gb")
    opts.add_argument("--disable-webgl")


    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )

    lista_de_imoveis = []
    
    try:
        driver.get("https://www.quintoandar.com.br/alugar/imovel/bela-vista-sao-paulo-sp-brasil?referrer=home&profiling=true")

        driver.execute_script("document.getElementById('cookies-component').remove();")

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "/html/body/div[1]/div/div/main/section[2]/div/div[2]/div[2]/div")
            )
        )

        print_thread = threading.Thread(target=print_imoveis_carregados, args=(driver,))
        print_thread.start()

        while True:
            try:
                botao_ver_mais = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[aria-label="Ver mais"].Cozy__Button-Component.bvu7K9.Pwr-5A.BDubiF')
                    )
                )
                botao_ver_mais.click()
                sleep(0.5)
            except (NoSuchElementException, TimeoutException):
                print(
                    "Botão 'Ver Mais' não encontrado. Todos os imóveis foram carregados."
                )
                break

            # Coletar os dados dos imóveis a cada clique no botão "Ver Mais"
            page_content = driver.page_source
            site = BeautifulSoup(page_content, "html.parser")

            imoveis = driver.find_elements(By.XPATH, "/html/body/div[1]/div/div/main/section[2]/div/div[2]/div[2]/div/a")

            for imovel in imoveis:
                titulo_text = imovel.get_attribute("title")
                setor = extrair_setor(titulo_text)

                link = imovel.get_attribute("href")

                imovel_html = imovel.get_attribute('outerHTML')
                imovel_soup = BeautifulSoup(imovel_html, 'html.parser')

                tipo = imovel_soup.find("p", attrs={"class": "card_split_vertically__type"})
                tipo_text = tipo.text.strip() if tipo else None

                preco_area = imovel_soup.find(
                    "div", attrs={"class": "card_split_vertically__value-container"}
                )
                preco = (
                    preco_area.find(
                        "p", attrs={"class": "card_split_vertically__value"}
                    ).text.strip()
                    if preco_area
                    else "Preço não especificado"
                )
                preco = "".join(
                    filter(str.isdigit, preco)
                )  # Remover caracteres não numéricos

                if (
                    not preco or preco == "0"
                ):  # Verificar se o preço está ausente ou igual a zero
                    continue  # Ignorar este imóvel e passar para o próximo

                metro = imovel_soup.find(
                    "li", attrs={"class": "card_split_vertically__spec"}
                )
                metro_text = metro.text.replace("m²", "").strip() if metro else None
                metro_text = "".join(
                    filter(str.isdigit, metro_text)
                )  # Remover caracteres não numéricos

                # quartos, suíte, banheiros, vagas
                quarto_suite_banheiro_vaga = imovel_soup.find(
                    "ul", attrs={"class": "card_split_vertically__specs"}
                )
                if quarto_suite_banheiro_vaga:
                    lista = quarto_suite_banheiro_vaga.findAll("li")
                    quarto = suite = banheiro = vaga = (
                        0  # Valor padrão 0 para substituir espaços em branco
                    )

                    for item in lista:
                        text_lower = item.text.lower()
                        if "quarto" in text_lower or "quartos" in text_lower:
                            quarto = int(
                                item.text.split()[0]
                            )  # Apenas o primeiro número
                        elif "suíte" in text_lower or "suítes" in text_lower:
                            suite = int(
                                item.text.split()[0]
                            )  # Apenas o primeiro número
                        elif "banheiro" in text_lower or "banheiros" in text_lower:
                            banheiro = int(
                                item.text.split()[0]
                            )  # Apenas o primeiro número
                        elif "vaga" in text_lower or "vagas" in text_lower:
                            vaga = int(item.text.split()[0])  # Apenas o primeiro número
                else:
                    quarto = suite = banheiro = vaga = 0

                # Adicionar informações à lista de imóveis apenas se não estiverem duplicadas
                if link not in [imovel[2] for imovel in lista_de_imoveis]:
                    lista_de_imoveis.append(
                        [
                            titulo_text,
                            tipo_text,
                            link,
                            preco,
                            metro_text,
                            quarto,
                            suite,
                            banheiro,
                            vaga,
                            setor,
                        ]
                    )

        return lista_de_imoveis

    except Exception as e:
        print(f"Ocorreu um erro durante o scraping: {e}")
        return lista_de_imoveis  # Retornar os dados coletados até o momento em caso de erro

    finally:
        driver.quit()


def salvar_excel(dataframe):
    dataframe.to_excel(
        r"C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\quinto_andar\quinto_andar.xlsx",
        index=False,
    )


def main():
    lista_de_imoveis = scrape_imoveis()

    df_imovel = pd.DataFrame(
        lista_de_imoveis,
        columns=[
            "Título",
            "Tipo",
            "Link",
            "Preço",
            "Metro Quadrado",
            "Quarto",
            "Suite",
            "Banheiro",
            "Vaga",
            "Setor",
        ],
    )

    df_imovel["Preço"] = pd.to_numeric(df_imovel["Preço"], errors="coerce")
    df_imovel["Metro Quadrado"] = pd.to_numeric(
        df_imovel["Metro Quadrado"], errors="coerce"
    )
    df_imovel["Quarto"] = pd.to_numeric(df_imovel["Quarto"], errors="coerce")
    df_imovel["Suite"] = pd.to_numeric(df_imovel["Suite"], errors="coerce")
    df_imovel["Banheiro"] = pd.to_numeric(df_imovel["Banheiro"], errors="coerce")
    df_imovel["Vaga"] = pd.to_numeric(df_imovel["Vaga"], errors="coerce")

    if df_imovel.isnull().values.any():
        print("Existem valores nulos no DataFrame. Lidar com eles conforme necessário.")

    df_imovel["M2"] = df_imovel["Preço"] / df_imovel["Metro Quadrado"]
    df_imovel[["Quarto", "Suite", "Banheiro", "Vaga", "M2"]] = df_imovel[
        ["Quarto", "Suite", "Banheiro", "Vaga", "M2"]
    ].fillna(0)

    salvar_excel(df_imovel)

    print(df_imovel)


if __name__ == "__main__":
    main()
