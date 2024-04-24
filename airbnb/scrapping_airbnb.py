import threading
from time import sleep

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def print_imoveis_carregados(driver):
    try:
        while True:
            sleep(5)
            imoveis_carregados = len(
                driver.find_elements(
                    By.XPATH, '//*[@rel="noopener noreferrer nofollow"]'
                )
            )
            print(f"Imóveis carregados: {imoveis_carregados}")
    except KeyboardInterrupt:
        pass


def scrape_imoveis():
    opts = Options()
    # opts.add_argument("--headless")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--memory-growth=10gb")
    chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )

    lista_de_imoveis = []

    try:
        driver.get(
            "https://www.airbnb.com.br/s/Distrito-Federal--Brasil/homes?tab_id=home_tab&refinement_paths%5B%5D=%2Fhomes&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2024-05-01&monthly_length=3&monthly_end_date=2024-08-01&price_filter_input_type=0&channel=EXPLORE&query=Distrito%20Federal%2C%20Brasil&place_id=ChIJ1wSIEPI6WpMRVlAUyZAjuj4&date_picker_type=calendar&source=structured_search_input_header&search_type=user_map_move&price_filter_num_nights=5&ne_lat=-14.939101975198565&ne_lng=-45.438454843542615&sw_lat=-18.043187916064145&sw_lng=-48.409272557982206&zoom=7.561746325642977&zoom_level=7.561746325642977&search_by_map=true"
        )

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, '//*[@rel="noopener noreferrer nofollow"]')
            )
        )

        print_thread = threading.Thread(target=print_imoveis_carregados, args=(driver,))
        print_thread.start()

        while True:
            try:
                botao_ver_mais = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (
                            By.XPATH,
                            '//*[@id="site-content"]/div/div[3]/div/div/div/nav/div/a[5]/svg',
                        )
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
            imoveis = site.find_all("a", attrs={"rel": "noopener noreferrer nofollow"})

            for imovel in imoveis:
                titulo = imovel.find("div", attrs={"data-testid": "listing-card-title"})
                titulo_text = titulo.text.strip() if titulo else None

                subtitulo = imovel.find("div", attrs={"class": "_b14dlit"})
                subtitulo_text = subtitulo.text.strip() if subtitulo else None

                link = "https://www.airbnb.com.br" + imovel["href"]

                camas = imovel.find("span", attrs={"class": " dir dir-ltr"})
                camas_text = camas.text.strip() if camas else None

                preco_area = imovel.find("span", attrs={"class": "_14y1gc"})
                preco = (
                    driver.find_elements(
                        By.XPATH,
                        '//*[@id="site-content"]/div/div[2]/div/div/div/div/div[1]/div[5]/div/div[2]/div/div/div/div/div/div[2]/div[5]/div[2]/div/div/span/span',
                    )[
                        0
                    ].text.strip()  # Note que usei [0] aqui para acessar o primeiro elemento da lista retornada por find_elements
                    if preco_area
                    else 0
                )
                preco = "".join(
                    filter(str.isdigit, preco)
                )  # Remover caracteres não numéricos

                if (
                    not preco or preco == "0"
                ):  # Verificar se o preço está ausente ou igual a zero
                    continue  # Ignorar este imóvel e passar para o próximo

                # Adicionar informações à lista de imóveis apenas se não estiverem duplicadas
                if link not in [imovel[2] for imovel in lista_de_imoveis]:
                    lista_de_imoveis.append(
                        [titulo_text, subtitulo_text, camas_text, link, preco]
                    )

        return lista_de_imoveis

    except Exception as e:
        print(f"Ocorreu um erro durante o scraping: {e}")
        return lista_de_imoveis  # Retornar os dados coletados até o momento em caso de erro

    finally:
        driver.quit()


def salvar_excel(dataframe):
    dataframe.to_excel(
        "C:/Users/galva/OneDrive/Documentos/GitHub/web-scrapping-com-python/airbnb/scrapping_airbnb.xlsx",
        index=False,
    )


def main():
    lista_de_imoveis = scrape_imoveis()

    df_imovel = pd.DataFrame(
        lista_de_imoveis,
        columns=[
            "Título",
            "Subtitulo",
            "Camas",
            "Link",
            "Preço",
        ],
    )

    df_imovel["Preço"] = pd.to_numeric(df_imovel["Preço"], errors="coerce")

    df_imovel.dropna(subset=["Preço"], inplace=True)

    df_imovel = df_imovel.sort_values(by=["Preço"], ascending=True)

    salvar_excel(df_imovel)


if __name__ == "__main__":
    main()
