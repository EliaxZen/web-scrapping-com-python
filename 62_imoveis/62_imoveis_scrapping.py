import requests
from bs4 import BeautifulSoup
import pandas as pd

lista_de_imoveis = []
pagina = 1

for pagina in range(130):
    pagina += 1
    resposta = requests.get(f'https://www.62imoveis.com.br/aluguel/df/brasilia/imoveis?pagina={pagina}')

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

        # quartos, suíte, vagas
        quarto_suite_vaga = imovel.find('ul', attrs={'class': 'new-details-ul'})
        lista = quarto_suite_vaga.text.split()
        
        

        lista_de_imoveis.append([titulo.text.strip(), subtitulo.text.strip() , link['href'], preco.text, metro.text.replace('m²', '').strip(), lista])
        



df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo', 'Link', 'Preço','Metro Quadrado', 'Metro, Quarto, Suite, Vaga'])
df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\62_imoveis\62_imoveis_scrapping.xlsx', index=False)