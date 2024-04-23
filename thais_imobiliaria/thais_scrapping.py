import requests
import pandas as pd
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options


opts = Options()
opts.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36")
#opts.add_argument("--headless")

# Alternativamente:
# driver = webdriver.Chrome(
#     service=Service('./chromedriver'),
#     options=opts
# )

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=opts
)

driver.get('https://www.thaisimobiliaria.com.br/imoveis/a-venda')

sleep(3)

page_content = driver.page_source

site = BeautifulSoup(page_content, 'html.parser')

imoveis = site.findAll('a', attrs={'class': 'card_split_vertically borderHover'})


sleep(2)
while True:
    try:
        # Espera até que o elemento dos cookies desapareça
        WebDriverWait(driver, 20).until(EC.invisibility_of_element_located((By.ID, "cookies-component")))
        # Verifica se o botão "Ver Mais" está presente na página
        botao_ver_mais = driver.find_element(By.CSS_SELECTOR, '.btn.btn-md.btn-primary.btn-next')
        
        # Se o botão estiver presente, clique nele
        botao_ver_mais.click()
        
        # Pausa temporária para aguardar o carregamento da próxima página
        sleep(1)  # Ajuste o tempo conforme necessário
        
    except NoSuchElementException:
        # Se o botão não estiver mais presente, saia do loop
        break

page_content = driver.page_source

site = BeautifulSoup(page_content, 'html.parser')
imoveis = site.findAll('a', attrs={'class': 'card_split_vertically borderHover'})

lista_de_imoveis = []


for imovel in imoveis:
        # Título do imóvel
        titulo = imovel.find('h2', attrs={'class': 'card_split_vertically__location'})
        titulo_text = titulo.text.strip() if titulo else None

        # Link do imovel
        link = 'https://www.thaisimobiliaria.com.br' + imovel['href']
        
        # Tipo do imóvel
        tipo = imovel.find('p', attrs={'class': 'card_split_vertically__type'})
        tipo_text = tipo.text.strip() if tipo else None

        # Preco aluguel
        preco = None
        preco_area = imovel.find('div', attrs={'class': 'card_split_vertically__value-container'})
        if preco_area:
                preco = preco_area.find('p', attrs={'class': 'card_split_vertically__value'})
                if preco:
                        preco = preco.text.strip()
                else:
                        preco = "Preço não especificado"
        else:
                preco = "Preço não especificado"


        # Metro quadrado
        metro = imovel.find('li', attrs={'class': 'card_split_vertically__spec'})
        metro_text = metro.text.replace('m²', '').strip() if metro else None


        # quartos, suíte, vagas
        quarto_suite_vaga = imovel.find('ul', attrs={'class': 'card_split_vertically__specs'})
        quarto_suite_vaga_lista = quarto_suite_vaga.text.split()
        # quarto = quarto_suite_vaga.text.replace('m²', '')[1:2]
        # suite = quarto_suite_vaga.text.replace('m²', '')[2:3]
        # banheiro = quarto_suite_vaga.text.replace('m²', '')[3:4]
        # vaga = quarto_suite_vaga.text.replace('m²', '')[4:5]
        # quarto_text = quarto.strip() if quarto else None
        # suite_text = suite.strip() if suite else None
        # vaga_text = vaga.strip() if vaga else None
        

        lista_de_imoveis.append([titulo_text, tipo_text, link, preco, metro_text, quarto_suite_vaga_lista])


df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Tipo', 'Link', 'Preço','Metro Quadrado', 'Quarto, Suite, Banheiro, Vaga'])

df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\thais_imobiliaria\imoveis_scrapping_thais_imobiliaria_venda.xlsx', index=False)

print(df_imovel)

