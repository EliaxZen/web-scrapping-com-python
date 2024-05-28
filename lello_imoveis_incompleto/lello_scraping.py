import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

lista_de_imoveis = []
links_processados = set()

for pagina in range(1, 10):
    print(f'Processando página: {pagina}')
    url = f'https://www.lelloimoveis.com.br/venda/residencial/sao_paulo-cidades/{pagina}-pagina/'
    resposta = requests.get(url)
    conteudo = resposta.content

    site = BeautifulSoup(conteudo, 'html.parser')
    imoveis = site.findAll('a', attrs={'itemprop': 'url'})

    for imovel in imoveis:
        try:
            # Link do imóvel
            link = 'https://www.lelloimoveis.com.br' + imovel.get('href')

            # Verificar se o link já foi processado
            if link in links_processados:
                continue

            # Verificar se cada elemento existe antes de acessá-lo
            titulo_elem = imovel.find('h3', attrs={'itemprop': 'streetAddress'})
            subtitulo_elem = imovel.find('span', attrs={'itemprop': 'addressLocality'})
            tipo_imovel_elem = imovel.find('div', attrs={'class': 'mb-2 card-title h5'})
            if tipo_imovel_elem:
                tipo_imovel_elem = tipo_imovel_elem.find('h2')
            preco_elem = imovel.find('div', attrs={'class': 'totalItemstyle__TotalItem-sc-t6cs2k-0'})
            if preco_elem:
                preco_elem = preco_elem.find('p', class_='mb-0 font-weight-bold')
            condominio_elem = imovel.find('div', attrs={'class': 'totalItemstyle__TotalItem-sc-t6cs2k-0'})
            if condominio_elem:
                condominio_elem = condominio_elem.find('p', class_='mb-1 f-1 text-neutral-dark')
            area_elem = imovel.find('meta', attrs={'itemprop': 'value'})
            quartos_elem = imovel.find('meta', attrs={'itemprop': 'numberOfBedrooms'})
            banheiros_elem = imovel.find('meta', attrs={'itemprop': 'numberOfBathroomsTotal'})
            vagas_elem = imovel.find('span', attrs={'data-testid': 'realty-parking-lot-quantity'})
            if vagas_elem:
                vagas_elem = vagas_elem.find('span', class_='tagItemstyle__TagValue-sc-13sggff-3')

            # Continuar apenas se todos os elementos necessários forem encontrados
            if all([titulo_elem, subtitulo_elem, tipo_imovel_elem, preco_elem, condominio_elem, area_elem, quartos_elem, banheiros_elem, vagas_elem]):
                titulo = titulo_elem.text.strip()
                subtitulo = subtitulo_elem.text.strip()
                tipo_imovel = tipo_imovel_elem.text.strip()
                preco = preco_elem.text.strip()
                condominio = condominio_elem.text.strip()
                area = area_elem['content']
                quartos = quartos_elem['content']
                banheiros = banheiros_elem['content']
                vagas = vagas_elem.text.strip()

                lista_de_imoveis.append([
                    titulo, subtitulo, tipo_imovel, link, preco, condominio, area, quartos, banheiros, vagas
                ])

                # Adicionar o link ao conjunto de links processados
                links_processados.add(link)
        except Exception as e:
            print(f"Erro ao processar imóvel: {e}")

# Criar DataFrame
df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo', 'Tipo Imóvel', 'Link', 'Preço', 'Condomínio', 'Área', 'Quartos', 'Banheiros', 'Vagas'])

# Remover duplicatas com base na coluna 'Link'
df_imovel = df_imovel.drop_duplicates(subset='Link')

# Função para limpar e converter colunas numéricas
def limpar_conversao_numerica(coluna):
    return pd.to_numeric(coluna.str.replace(r'\D', '', regex=True), errors='coerce')

# Aplicar função de limpeza nas colunas numéricas
df_imovel['Preço'] = limpar_conversao_numerica(df_imovel['Preço'])
df_imovel['Condomínio'] = limpar_conversao_numerica(df_imovel['Condomínio'])
df_imovel['Área'] = limpar_conversao_numerica(df_imovel['Área'])
df_imovel['Quartos'] = limpar_conversao_numerica(df_imovel['Quartos'])
df_imovel['Banheiros'] = limpar_conversao_numerica(df_imovel['Banheiros'])
df_imovel['Vagas'] = limpar_conversao_numerica(df_imovel['Vagas'])

# Remover imóveis sem preço ou área
df_imovel = df_imovel.dropna(subset=['Preço', 'Área'])

# Adicionar coluna M2
df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Área']

# Exibir DataFrame final
print(df_imovel)

# Salvar DataFrame em um arquivo Excel
df_imovel.to_excel('lello_imoveis.xlsx', index=False)
