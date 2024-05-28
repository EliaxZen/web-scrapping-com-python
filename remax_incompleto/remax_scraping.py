import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

lista_de_imoveis = []
links_processados = set()

for pagina in range(1, 10):
    print(f'Processando página: {pagina}')
    url = f'https://www.remax.com.br/PublicListingList.aspx#mode=gallery&tt=261&cur=BRL&sb=MostRecent&page={pagina}&sc=55&pm=9523&lsgeo=0,9523,0,0&sid=ba6197c6-fb1d-43a8-898e-635b72029ea5'
    resposta = requests.get(url)
    conteudo = resposta.content

    site = BeautifulSoup(conteudo, 'html.parser')
    imoveis = site.findAll('div', attrs={'class': 'gallery-item-container'})

    for imovel in imoveis:
        try:
            # Link do imóvel
            link_elem = imovel.find('div', class_='gallery-title').find('a')
            link = 'https://www.remax.com.br' + link_elem['href']
            print(f"Link: {link}")  # Debug statement

            # Verificar se o link já foi processado
            if link in links_processados:
                continue

            # Título do imóvel
            titulo = link_elem['title']
            print(f"Título: {titulo}")  # Debug statement

            # Preço do imóvel
            preco_elem = imovel.find('span', class_='gallery-price-main').find('a', class_='proplist_price')
            preco = preco_elem.text.strip() if preco_elem else None
            print(f"Preço: {preco}")  # Debug statement

            # Tipo do imóvel
            tipo_imovel_elem = imovel.find('div', class_='gallery-transtype').find('span')
            tipo_imovel = tipo_imovel_elem.text.strip() if tipo_imovel_elem else None
            print(f"Tipo Imóvel: {tipo_imovel}")  # Debug statement

            # Área, Dormitórios, Banheiros e Ambientes Totais
            area_elem = imovel.find('img', src="/common/images/2019/Sq-meter.svg")
            area = area_elem.find_next_sibling('span', class_='gallery-attr-item-value').text.strip() if area_elem else None
            print(f"Área: {area}")  # Debug statement

            quartos_elem = imovel.find('img', src="/common/images/2019/bedrooms.svg")
            quartos = quartos_elem.find_next_sibling('span', class_='gallery-attr-item-value').text.strip() if quartos_elem else None
            print(f"Quartos: {quartos}")  # Debug statement

            banheiros_elem = imovel.find('img', src="/common/images/2019/bathrooms.svg")
            banheiros = banheiros_elem.find_next_sibling('span', class_='gallery-attr-item-value').text.strip() if banheiros_elem else None
            print(f"Banheiros: {banheiros}")  # Debug statement

            ambientes_totais_elem = imovel.find('img', src="/common/images/2019/total-rooms.svg")
            ambientes_totais = ambientes_totais_elem.find_next_sibling('span', class_='gallery-attr-item-value').text.strip() if ambientes_totais_elem else None
            print(f"Ambientes Totais: {ambientes_totais}")  # Debug statement

            # Adicionando informações na lista de imóveis
            lista_de_imoveis.append([
                titulo, link, preco, tipo_imovel, area, quartos, banheiros, ambientes_totais
            ])

            # Adicionar o link ao conjunto de links processados
            links_processados.add(link)
        except Exception as e:
            print(f"Erro ao processar imóvel: {e}")

# Criar DataFrame
df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Link', 'Preço', 'Tipo Imóvel', 'Área', 'Quartos', 'Banheiros', 'Ambientes Totais'])

# Remover duplicatas com base na coluna 'Link'
df_imovel = df_imovel.drop_duplicates(subset='Link')

# Função para limpar e converter colunas numéricas
def limpar_conversao_numerica(coluna):
    return pd.to_numeric(coluna.str.replace(r'\D', '', regex=True), errors='coerce')

# Aplicar função de limpeza nas colunas numéricas
df_imovel['Preço'] = limpar_conversao_numerica(df_imovel['Preço'])
df_imovel['Área'] = limpar_conversao_numerica(df_imovel['Área'])
df_imovel['Quartos'] = limpar_conversao_numerica(df_imovel['Quartos'])
df_imovel['Banheiros'] = limpar_conversao_numerica(df_imovel['Banheiros'])
df_imovel['Ambientes Totais'] = limpar_conversao_numerica(df_imovel['Ambientes Totais'])

# Remover imóveis sem preço ou área
df_imovel = df_imovel.dropna(subset=['Preço', 'Área'])

# Adicionar coluna M2
df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Área']

# Exibir DataFrame final
print(df_imovel)

# Salvar DataFrame em um arquivo Excel
df_imovel.to_excel('remax_imoveis.xlsx', index=False)
print(resposta)
