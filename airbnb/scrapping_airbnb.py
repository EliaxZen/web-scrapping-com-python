import pandas as pd
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException

opts = Options()
opts.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36")
# opts.add_argument("--headless")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=opts
)

driver.get('https://www.airbnb.com.br/s/Distrito-Federal--Brasil/homes?tab_id=home_tab&refinement_paths%5B%5D=%2Fhomes&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2024-05-01&monthly_length=3&monthly_end_date=2024-08-01&price_filter_input_type=0&channel=EXPLORE&query=Distrito%20Federal%2C%20Brasil&place_id=ChIJ1wSIEPI6WpMRVlAUyZAjuj4&date_picker_type=calendar&source=structured_search_input_header&search_type=filter_change&price_filter_num_nights=5')

while True:
    page_content = driver.page_source
    site = BeautifulSoup(page_content, 'html.parser')
    imoveis = site.findAll('div', attrs={'data-testid': 'card-container'})

    lista_de_imoveis = []

    for imovel in imoveis:
        titulo = imovel.find('div', attrs={'data-testid': 'listing-card-title'})
        titulo_text = titulo.text.strip() if titulo else None
        
        subtitulo = imovel.find('span', attrs={'data-testid': 'listing-card-name'})
        subtitulo_text = subtitulo.text.strip() if subtitulo else None

        link = 'https://www.airbnb.com.br/' + imovel.find('a')['href']
        
        tipo = imovel.find('p', attrs={'class': 'card_split_vertically__type'})
        tipo_text = tipo.text.strip() if tipo else None

        preco = imovel.find('span', attrs={'class': 'a8jt5op atm_3f_idpfg4 atm_7h_hxbz6r atm_7i_ysn8ba atm_e2_t94yts atm_ks_zryt35 atm_l8_idpfg4 atm_mk_stnw88 atm_vv_1q9ccgz atm_vy_t94yts dir dir-ltr'})

        lista_de_imoveis.append([titulo_text, subtitulo_text, link, preco])

    df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtitulo', 'Link', 'Preço'])
    df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\thais_imobiliaria\imoveis_scrapping_thais_imobiliaria_venda.xlsx', index=False)
    print(df_imovel)

    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[aria-label=Próximo]'))).click()
        sleep(2)  # Aguarde o carregamento da próxima página
    except TimeoutException:
        break  # Se não houver mais botão "Próximo", saia do loop

driver.quit()
