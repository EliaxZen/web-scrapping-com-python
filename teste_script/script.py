import requests
from bs4 import BeautifulSoup
import pandas as pd

lista_de_imoveis = []
pagina = 1

for pagina in range(245):
    pagina += 1
    resposta = requests.get(f'https://www.dfimoveis.com.br/aluguel/df/todos/imoveis?pagina={pagina}')

    conteudo = resposta.content

    site = BeautifulSoup(conteudo, 'html.parser')

    # HTML do anúncio do imóvel
    imoveis = site.findAll('a', attrs={'class': 'new-card'})

    for imovel in imoveis:
        # Título do imóvel
        titulo = imovel.find('h2', attrs={'class': 'new-title'})

        # Link do imovel
        link = site.find('a', attrs={'class': 'new-card'})

        # Subtítulo do imóvel
        subtitulo = imovel.find('h3', attrs={'class': 'new-simple'})

        # Preco aluguel
        preco_area = imovel.find('div', attrs={'class': 'new-price'})
        preco = preco_area.find('h4')

        # Metro quadrado
        metro = imovel.find('li', attrs={'class': 'm-area'})

        if (subtitulo):
            lista_de_imoveis.append([titulo.text.strip(), subtitulo.text.strip() , link['href'], preco.text, metro.text.replace('m²', '').strip()])
        else:
            lista_de_imoveis.append([titulo.text, '',link['href'], preco.text, metro.text.replace('m²', '').strip()])



df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo', 'Link', 'Preço', 'Metro Quadrado'])
df_imovel.to_excel('primeiro_web_scrapping.xlsx', index=False)
