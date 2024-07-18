# Obtendo produtos do Mercado Livre a partir de uma busca personalizada pelo usuáro.

import requests
from bs4 import BeautifulSoup
import pandas as pd

lista_de_produtos = []

url_base = 'https://lista.mercadolivre.com.br/'

produto_nome = input('Qual produto você deseja? ')

response = requests.get(url_base + produto_nome)

site = BeautifulSoup(response.text, 'html.parser')

produtos = site.findAll('div', attrs={'class': 'andes-card ui-search-result ui-search-result--core andes-card--flat andes-card--padding-16'})

for produto in produtos:
    titulo = produto.find('h2', attrs={'class': 'ui-search-item__title'})

    link = produto.find('a', attrs={'class': 'ui-search-item__group__element ui-search-link__title-card ui-search-link'})

    real = produto.find('span', attrs={'class': 'andes-money-amount__fraction'})
    centavos = produto.find('span', attrs={'class': 'andes-money-amount__cents andes-money-amount__cents--superscript-24'})


    if (centavos):
        lista_de_produtos.append([titulo.text, link['href'], real.text + ',' + centavos.text])
    else:
        lista_de_produtos.append([titulo.text, link['href'], real.text])

df_produtos_mercado_livre = pd.DataFrame(lista_de_produtos, columns=['Título', 'Link', 'Preço',])
df_produtos_mercado_livre.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\mercado_livre\mercado_livre_scrapping.xlsx', index=False)