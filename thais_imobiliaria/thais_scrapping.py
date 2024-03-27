# import requests
# import pandas as pd
# from time import sleep
# from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.chrome.service import Service as ChromeService
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import NoSuchElementException

# navegador = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

# # Create a service object with the driver path

# navegador.get('https://www.thaisimobiliaria.com.br/imoveis/a-venda')

# sleep(2)
# while True:
#     try:
#         # Espera até que o elemento dos cookies desapareça
#         WebDriverWait(navegador, 20).until(EC.invisibility_of_element_located((By.ID, "cookies-component")))
#         # Verifica se o botão "Ver Mais" está presente na página
#         botao_ver_mais = navegador.find_element(By.CSS_SELECTOR, '.btn.btn-md.btn-primary.btn-next')
        
#         # Se o botão estiver presente, clique nele
#         botao_ver_mais.click()
        
#         # Pausa temporária para aguardar o carregamento da próxima página
#         sleep(10)  # Ajuste o tempo conforme necessário
        
#     except NoSuchElementException:
#         # Se o botão não estiver mais presente, saia do loop
#         break

# page_content = navegador.page_source

# site = BeautifulSoup(page_content, 'html.parser')
# imoveis = site.findAll('a', attrs={'class': 'card_split_vertically borderHover'})

# lista_de_imoveis = []


# for imovel in imoveis:
#         # Título do imóvel
#         titulo = imovel.find('h2', attrs={'class': 'card_split_vertically__location'})
#         titulo_text = titulo.text.strip() if titulo else None

#         # Link do imovel
#         link = 'https://www.thaisimobiliaria.com.br' + imovel['href']
        
#         # Tipo do imóvel
#         tipo = imovel.find('p', attrs={'class': 'card_split_vertically__type'})
#         tipo_text = tipo.text.strip() if tipo else None

#         # Preco aluguel
#         preco = None
#         preco_area = imovel.find('div', attrs={'class': 'card_split_vertically__value-container'})
#         if preco_area:
#                 preco = preco_area.find('p', attrs={'class': 'card_split_vertically__value'})
#                 if preco:
#                         preco = preco.text.strip()
#                 else:
#                         preco = "Preço não especificado"
#         else:
#                 preco = "Preço não especificado"


#         # Metro quadrado
#         metro = imovel.find('li', attrs={'class': 'card_split_vertically__spec'})
#         metro_text = metro.text.replace('m²', '').strip() if metro else None


#         # quartos, suíte, vagas
#         quarto_suite_vaga = imovel.find('ul', attrs={'class': 'card_split_vertically__specs'})
#         quarto_suite_vaga_lista = quarto_suite_vaga.text.split()
#         # quarto = quarto_suite_vaga.text.replace('m²', '')[1:2]
#         # suite = quarto_suite_vaga.text.replace('m²', '')[2:3]
#         # banheiro = quarto_suite_vaga.text.replace('m²', '')[3:4]
#         # vaga = quarto_suite_vaga.text.replace('m²', '')[4:5]
#         # quarto_text = quarto.strip() if quarto else None
#         # suite_text = suite.strip() if suite else None
#         # vaga_text = vaga.strip() if vaga else None
        

#         lista_de_imoveis.append([titulo_text, tipo_text, link, preco, metro_text, quarto_suite_vaga_lista])


# df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Tipo', 'Link', 'Preço','Metro Quadrado', 'Quarto, Suite, Banheiro, Vaga'])

# df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\thais_imobiliaria\imoveis_scrapping_thais_imobiliaria_venda.xlsx', index=False)

# print(df_imovel)
# navegador.quit()



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

navegador = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

# Create a service object with the driver path

navegador.get('https://www.thaisimobiliaria.com.br/imoveis/a-venda?pagina=1')

sleep(2)





lista_de_imoveis = []
pagina = 1

for pagina in range(309):
    pagina += 1
    resposta = requests.get(f'https://www.thaisimobiliaria.com.br/imoveis/a-venda?pagina={pagina}')

    conteudo = resposta.content


    page_content = navegador.page_source
    site = BeautifulSoup(page_content, 'html.parser')

    # HTML do anúncio do imóvel
    imoveis = site.findAll('a', attrs={'class': 'card_split_vertically borderHover'})

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
        # banheiro_text = banheiro.strip() if banheiro else None
        # vaga_text = vaga.strip() if vaga else None
        
        

        lista_de_imoveis.append([titulo_text, tipo_text, link, preco, metro_text, quarto_suite_vaga_lista])


df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Tipo', 'Link', 'Preço','Metro Quadrado', 'Quarto...'])

df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\thais_imobiliaria\imoveis_scrapping_thais_imobiliaria_venda.xlsx', index=False)

print(df_imovel)
navegador.quit()