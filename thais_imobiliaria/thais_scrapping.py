import requests
import pandas as pd
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

driver_path = ChromeDriverManager().install()

# Create a service object with the driver path
service = Service(driver_path)

navegador = webdriver.Chrome(service=service)

navegador.get('https://www.thaisimobiliaria.com.br/imoveis/a-venda/brasilia')

sleep(2)

page_content = navegador.page_source

site = BeautifulSoup(page_content, 'html.parser')

imoveis = site.findAll('a', attrs={'class': 'card_split_vertically borderHover'})

lista_de_imoveis = []

for imovel in imoveis:
        # Título do imóvel
        titulo = imovel.find('h2', attrs={'class': 'card_split_vertically__location'})

        # Link do imovel
        link = 'https://www.thaisimobiliaria.com.br' + imovel['href']
        
        # Tipo do imóvel
        tipo = imovel.find('p', attrs={'class': 'card_split_vertically__type'})

        # Preco aluguel
        preco_area = imovel.find('div', attrs={'class': 'card_split_vertically__value-container'})
        preco = preco_area.find('p', attrs={'class': 'card_split_vertically__value'})

        # Metro quadrado
        metro = imovel.find('li', attrs={'class': 'card_split_vertically__spec'})

        # quartos, suíte, vagas
        quarto_suite_vaga = imovel.find('ul', attrs={'class': 'card_split_vertically__specs'})
        quarto = quarto_suite_vaga.text.replace('m²', '')[1:2]
        suite = quarto_suite_vaga.text.replace('m²', '')[2:3]
        banheiro = quarto_suite_vaga.text.replace('m²', '')[3:4]
        vaga = quarto_suite_vaga.text.replace('m²', '')[4:5]
        
        

        lista_de_imoveis.append([titulo.text.strip(), tipo.text.strip() , link, preco.text, metro.text.replace('m²', '').strip(), quarto, suite, banheiro, vaga])

df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Tipo', 'Link', 'Preço','Metro Quadrado', 'Quarto', 'Suite', 'Banheiro', 'Vaga'])

df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\thais_imobiliaria\imoveis_scrapping_thais_imobiliaria.xlsx', index=False)

print(df_imovel)
navegador.quit()
driver.quit()