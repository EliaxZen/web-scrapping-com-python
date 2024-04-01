import requests
from bs4 import BeautifulSoup
import pandas as pd

lista_de_imoveis = []
pagina = 1

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

for pagina in range(1400):
    pagina += 1
    url = f'https://www.zapimoveis.com.br/venda/imoveis/df+brasilia/?__ab=exp-aa-test:B,rec-cta:control&transacao=venda&onde=,Distrito%20Federal,Bras%C3%ADlia,,,,,city,BR%3EDistrito%20Federal%3ENULL%3EBrasilia,-15.826691,-47.92182,&pagina={pagina}'
    resposta = requests.get(url, headers=headers)
    conteudo = resposta.content

    site = BeautifulSoup(conteudo, 'html.parser')

    # HTML do anúncio do imóvel
    imoveis = site.findAll('a', attrs={'class': 'result-card result-card__highlight result-card__highlight--standard'})

    for imovel in imoveis:
        # Título do imóvel
        titulo = imovel.find('div', attrs={'data-cy': 'card__address'})
        titulo_text = titulo.text if titulo else None

        # Subtítulo do imóvel
        subtitulo = imovel.find('p', attrs={'class': 'l-text l-u-color-neutral-28 l-text--variant-body-small l-text--weight-regular card__street'})
        subtitulo_text = subtitulo.text.strip() if subtitulo else None

        # Link do imovel
        # Link do imovel
        link = imovel['href']


        # Preco aluguel
        preco_area = imovel.find('div', attrs={'class': 'listing-price'})
        preco = preco_area.find('p')
        preco_text = preco.text if preco else None

        # Metro quadrado
        metro_area = imovel.find('section', attrs={'class': 'card__amenities'})
        metro = metro_area.find('p', itemprop='floorSize') if metro_area else None
        metro_text = metro.text.replace('m²', '').strip() if metro else 0

        # quartos, banheiro, vagas
        # quarto_banheiro_vaga = imovel.find('section', attrs={'class': 'card__amenities'})
        # lista = quarto_banheiro_vaga.text.replace('m²', '').split() if quarto_banheiro_vaga else None

        # Quartos
        quarto = imovel.find('p', itemprop='numberOfRooms') if metro_area else None
        quarto_text = quarto.text if quarto else 0
        
        # Banheiros
        banheiro = metro_area.find('p', itemprop='numberOfBathroomsTotal') if metro_area else None
        banheiro_text = banheiro.text if banheiro else 0
        
        # Vagas/Garagem
        garagem = metro_area.find('p', itemprop='numberOfParkingSpaces') if metro_area else None
        garagem_text = garagem.text if garagem else 0
        
        
        
        lista_de_imoveis.append([titulo_text, subtitulo_text, link, preco_text, metro_text, quarto_text, banheiro_text, garagem_text])
        #lista_de_imoveis.append([titulo_text, subtitulo_text, link, preco_text, lista])


        



df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo/Setor', 'Link', 'Preço','Metro Quadrado', 'Quarto', 'Banheiro', 'Vaga'])
df_imovel.to_excel(r'C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\zap_imoveis\zap_imoveis_teste.xlsx', index=False)
print(resposta)
print(df_imovel)