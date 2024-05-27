import requests
from bs4 import BeautifulSoup
import pandas as pd

lista_de_imoveis = []
links_processados = set()

for pagina in range(1, 10):
    print(f'Processando página: {pagina}')
    url = f'https://www.lopes.com.br/busca/venda/br/sp/sao-paulo/pagina/{pagina}?estagio=real_estate&estagio=real_estate_parent&placeId=ChIJ0WGkg4FEzpQRrlsz_whLqZs'
    resposta = requests.get(url)
    conteudo = resposta.content

    site = BeautifulSoup(conteudo, 'html.parser')
    imoveis = site.findAll('div', attrs={'class': 'card ng-star-inserted'})

    for imovel in imoveis:
        try:
            # Link do imóvel
            link_elem = imovel.find('a')
            link = 'https://www.lopes.com.br' + link_elem['href']
            print(f"Link: {link}")  # Debug statement

            # Verificar se o link já foi processado
            if link in links_processados:
                continue

            # Título do imóvel
            titulo = link_elem.find('img')['alt']
            print(f"Título: {titulo}")  # Debug statement

            # Preço do imóvel
            preco_elem = imovel.find('h4', class_='card__price ng-star-inserted')
            preco = preco_elem.text.strip() if preco_elem else None
            print(f"Preço: {preco}")  # Debug statement

            # Tipo do imóvel
            tipo_imovel_elem = imovel.find('p', class_='card__type ng-star-inserted')
            tipo_imovel = tipo_imovel_elem.text.strip() if tipo_imovel_elem else None
            print(f"Tipo Imóvel: {tipo_imovel}")  # Debug statement

            # Localização do imóvel
            localizacao_elems = imovel.find_all('p', class_='card__location')
            localizacao = ", ".join([loc.text.strip() for loc in localizacao_elems])
            print(f"Localização: {localizacao}")  # Debug statement

            # Área, Dormitórios, Banheiros e Garagens
            area_elem = imovel.find('lps-icon-ruler').find_next('div', class_='attributes__value')
            area = area_elem.text.strip().replace('m²', '') if area_elem else None
            print(f"Área: {area}")  # Debug statement

            quartos_elem = imovel.find('lps-icon-bed').find_next('div', class_='attributes__value')
            quartos = quartos_elem.text.strip() if quartos_elem else None
            print(f"Quartos: {quartos}")  # Debug statement

            banheiros_elem = imovel.find('lps-icon-sink').find_next('div', class_='attributes__value')
            banheiros = banheiros_elem.text.strip() if banheiros_elem else None
            print(f"Banheiros: {banheiros}")  # Debug statement

            garagens_elem = imovel.find('lps-icon-car').find_next('div', class_='attributes__value')
            garagens = garagens_elem.text.strip() if garagens_elem else None
            print(f"Garagens: {garagens}")  # Debug statement

            # Adicionando informações na lista de imóveis
            lista_de_imoveis.append([
                titulo, link, preco, tipo_imovel, localizacao, area, quartos, banheiros, garagens
            ])

            # Adicionar o link ao conjunto de links processados
            links_processados.add(link)
        except Exception as e:
            print(f"Erro ao processar imóvel: {e}")

# Criar DataFrame
df_imovel = pd.DataFrame(lista_de_imoveis, columns=[
    'Título', 'Link', 'Preço', 'Tipo Imóvel', 'Localização', 'Área', 'Quartos', 'Banheiros', 'Garagens'
])

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
df_imovel['Garagens'] = limpar_conversao_numerica(df_imovel['Garagens'])

# Remover imóveis sem preço ou área
df_imovel = df_imovel.dropna(subset=['Preço', 'Área'])

# Adicionar coluna M2
df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Área']

# Exibir DataFrame final
print(df_imovel)

# Salvar DataFrame em um arquivo Excel
df_imovel.to_excel('lopes_imoveis.xlsx', index=False)
print(resposta)
