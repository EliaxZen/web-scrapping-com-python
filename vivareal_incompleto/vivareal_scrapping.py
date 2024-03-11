import requests
from bs4 import BeautifulSoup
import pandas as pd

lista_de_imoveis = []

# Loop para acessar apenas a página 1
for pagina in range(1):
    url = f'https://www.vivareal.com.br/aluguel/distrito-federal/brasilia/?pagina={pagina + 1}#onde=,Distrito%20Federal,Bras%C3%ADlia,,,,,,BR%3EDistrito%20Federal%3ENULL%3EBrasilia,,,'

    # Fazendo a requisição HTTP com um cabeçalho de agente de usuário
    resposta = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    resposta.raise_for_status()  # Lança uma exceção para erros HTTP
    conteudo = resposta.content

    site = BeautifulSoup(conteudo, 'html.parser')

    # Encontrando todos os elementos HTML que representam os anúncios de imóveis
    imoveis = site.findAll('article', attrs={'class': 'property-card__container js-property-card'})

    for imovel in imoveis:
        # Extraindo informações do imóvel
        titulo = imovel.find('span', attrs={'class': 'property-card__address'})
        titulo_texto = titulo.text.strip() if titulo else None

        link = imovel.find('a', attrs={'class': 'property-card__content-link js-card-title'})
        link_href = link['href'] if link else None
        link_completo = f"https://www.vivareal.com.br{link_href}" if link_href else None

        subtitulo = imovel.find('span', attrs={'class': 'property-card__title js-cardLink js-card-title'})
        subtitulo_texto = subtitulo.text.strip() if subtitulo else None

        preco_area = imovel.find('div', attrs={'class': 'property-card__price js-property-card-prices js-property-card__price-small'})
        preco = preco_area.find('p').text.strip().replace('/Mês', '') if preco_area else None

        metro = imovel.find('span', attrs={'class': 'property-card__detail-value js-property-card-value property-card__detail-area js-property-card-detail-area'})
        metro_texto = metro.text.strip() if metro else None

        quarto = imovel.find('span', attrs={'class': 'property-card__detail-value js-property-card-value'})
        quarto_texto = quarto.text.strip() if quarto else None

        banheiro = imovel.find('span', attrs={'class': 'property-card__detail-value js-property-card-value'})
        banheiro_texto = banheiro.text.strip() if banheiro else None

        vaga = imovel.find('span', attrs={'class': 'property-card__detail-value js-property-card-value'})
        vaga_texto = vaga.text.strip() if vaga else None

        variaveis_dumizaveis = imovel.find('ul', attrs={'class': 'property-card__amenities'})
        variaveis_dumizaveis_texto = variaveis_dumizaveis.text.strip() if variaveis_dumizaveis else None

        # Adicionando informações do imóvel à lista
        lista_de_imoveis.append([titulo_texto, subtitulo_texto, link_completo, preco, metro_texto, quarto_texto, banheiro_texto, vaga_texto, variaveis_dumizaveis_texto])

# Criando DataFrame com as informações coletadas
df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo', 'Link', 'Preço', 'Metro Quadrado', 'Quarto', 'Banheiro', 'Vaga', 'Variaveis Du'])

# Salvando o DataFrame em um arquivo Excel
df_imovel.to_excel('imoveis.xlsx', index=False)

# Exibindo o DataFrame
df_imovel

