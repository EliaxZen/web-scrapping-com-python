import requests
from bs4 import BeautifulSoup
import pandas as pd

lista_de_imoveis = []

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

for pagina in range(721):
    pagina += 1
    url = f'https://www.wimoveis.com.br/terrenos-venda-distrito-federal-pagina-{pagina}.html'
    resposta = requests.get(url, headers=headers)
    conteudo = resposta.content

    site = BeautifulSoup(conteudo, 'html.parser')

    # HTML do anúncio do imóvel
    imoveis = site.findAll('div', attrs={'class': 'sc-i1odl-0 dreQQz'})

    for imovel in imoveis:
        # Título do imóvel
        titulo = imovel.find('div', attrs={'class': 'sc-ge2uzh-0 eWOwnE postingAddress'})
        titulo_text = titulo.text if titulo else None

        # Subtítulo do imóvel
        subtitulo = imovel.find('h2', attrs={'data-qa': 'POSTING_CARD_LOCATION'})
        subtitulo_text = subtitulo.text.strip() if subtitulo else None

        # Link do imovel
        link = 'https://www.wimoveis.com.br' + imovel['data-to-posting']

        # Preco aluguel
        preco = imovel.find('div', attrs={'data-qa': 'POSTING_CARD_PRICE'})
        preco_text = preco.text if preco else None

        # Metro quadrado
        metro_area = imovel.find('h3', attrs={'data-qa': 'POSTING_CARD_FEATURES'})
        metro = metro_area.find('span') if metro_area else None
        metro_text = metro.text.replace('m²', '').strip() if metro else None

        # quartos, suíte, vagas
        quarto_suite_vaga = imovel.find('h3', attrs={'data-qa': 'POSTING_CARD_FEATURES'})
        if quarto_suite_vaga:
            lista = quarto_suite_vaga.find_all('span')
            quarto = banheiro = vaga = None

            for item in lista:
                if 'quarto' in item.text.lower():
                    quarto = item.text
                elif 'banheiro' in item.text.lower():
                    banheiro = item.text
                elif 'vaga' in item.text.lower():
                    vaga = item.text
        else:
            quarto = banheiro = vaga = None

        lista_de_imoveis.append([titulo_text, subtitulo_text, link, preco_text, metro_text, quarto, banheiro, vaga])

df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo', 'Link', 'Preço', 'Metro Quadrado', 'Quarto', 'Banheiro', 'Vaga'])
df_imovel.to_excel('wimoveis_scrapping_venda_lote_terreno.xlsx', index=False)
print(df_imovel)
