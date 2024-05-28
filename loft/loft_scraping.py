import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

lista_de_imoveis = []
links_processados = set()

for pagina in range(1, 132):
    print(f'Processando página: {pagina}')
    url = f'https://loft.com.br/venda/imoveis/sp/sao-paulo?utm_source=google&utm_medium=cpc&utm_campaign=ins_01_br_001_sp_0001_sao-paulo_all_aw_search_conversion_broad_&utm_content=loft-geral&utm_id=1756086660&utm_placement=&utm_ad_id=688886764052&utm_term=loft&gad_source=1&gbraid=0AAAAAC7BpWK3-sZlmGSJ5q6mBHbXZO8Fk&pagina={pagina}'
    resposta = requests.get(url)
    conteudo = resposta.content

    site = BeautifulSoup(conteudo, 'html.parser')
    imoveis = site.findAll('a', class_='MuiButtonBase-root MuiCardActionArea-root jss317')

    for imovel in imoveis:
        try:
            # Link do imóvel
            link = 'https://loft.com.br' + imovel['href']
            print(f"Link: {link}")  # Debug statement

            # Verificar se o link já foi processado
            if link in links_processados:
                continue

            # Título do imóvel
            titulo = None
            titulo_seletores = [
                'div.jss322 div.jss324 div.jss323 h2',
                'h2.MuiTypography-root.jss201.jss179.jss192.jss366.MuiTypography-body1.MuiTypography-noWrap',
                '#__next > section > div.jss2028 > div.jss2029 > div > div.MuiGrid-root.jss173.lgMaxWidth.MuiGrid-container > div:nth-child(21) > a > div.jss316 > div > h2',
                '/html/body/div[1]/section/div[4]/div[1]/div/div[1]/div[21]/a/div[2]/div/h2'
            ]
            for seletor in titulo_seletores:
                titulo_elem = imovel.select_one(seletor)
                if titulo_elem:
                    titulo = titulo_elem.text.strip()
                    break
            print(f"Título: {titulo}")  # Debug statement

            # Preço do imóvel
            preco = None
            preco_seletores = [
                'div.jss322 div.jss324 div.jss323 div div span',
                'span.MuiTypography-root.jss201.jss178.jss189.jss362.MuiTypography-body1',
                '#__next > section > div.jss1889 > div.jss1890 > div > div.MuiGrid-root.jss173.lgMaxWidth.MuiGrid-container > div:nth-child(37) > a > div.jss316 > div > div.jss359 > div > div:nth-child(1) > span',
                'span.MuiTypography-root.jss201.jss178.jss189.jss362.MuiTypography-body1',
                '/html/body/div[1]/section/div[4]/div[1]/div/div[1]/div[37]/a/div[2]/div/div[1]/div/div[1]/span'
            ]
            for seletor in preco_seletores:
                preco_elem = imovel.select_one(seletor)
                if preco_elem:
                    preco = preco_elem.text.strip()
                    break
            print(f"Preço: {preco}")  # Debug statement

            # Tipo do imóvel
            tipo_imovel = None
            tipo_imovel_elem = imovel.find('span', id='property-type')
            if tipo_imovel_elem:
                tipo_imovel = tipo_imovel_elem.text.strip()
            print(f"Tipo Imóvel: {tipo_imovel}")  # Debug statement

            # Área
            area = None
            area_seletores = [
                'div.jss322 div.jss324 div.jss323 div div span:nth-of-type(1)',
                'span.MuiTypography-root.jss201.jss179.jss190.MuiTypography-body1.MuiTypography-noWrap',
                '#__next > section > div.jss2028 > div.jss2029 > div > div.MuiGrid-root.jss173.lgMaxWidth.MuiGrid-container > div:nth-child(21) > a > div.jss316 > div > div.jss357 > div > div:nth-of-type(1) > span',
                '/html/body/div[1]/section/div[4]/div[1]/div/div[1]/div[21]/a/div[2]/div/div[2]/div/div[1]/span'
            ]
            for seletor in area_seletores:
                area_elem = imovel.select_one(seletor)
                if area_elem:
                    area = area_elem.text.strip()
                    break
            print(f"Área: {area}")  # Debug statement

            # Quartos
            quartos_elem = imovel.select('span.MuiTypography-root.jss201.jss179.jss190.MuiTypography-body1.MuiTypography-noWrap')[1]
            quartos = quartos_elem.text.strip() if quartos_elem else None
            print(f"Quartos: {quartos}")  # Debug statement

            # Vagas
            vagas_elem = imovel.select('span.MuiTypography-root.jss201.jss179.jss190.MuiTypography-body1.MuiTypography-noWrap')[2]
            vagas = vagas_elem.text.strip() if vagas_elem else None
            print(f"Vagas: {vagas}")  # Debug statement

            # Adicionando informações na lista de imóveis
            lista_de_imoveis.append([
                titulo, link, preco, tipo_imovel, area, quartos, vagas
            ])

            # Adicionar o link ao conjunto de links processados
            links_processados.add(link)
        except Exception as e:
            print(f"Erro ao processar imóvel: {e}")

# Criar DataFrame
df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Link', 'Preço', 'Tipo Imóvel', 'Área', 'Quartos', 'Vagas'])

# Remover duplicatas com base na coluna 'Link'
df_imovel = df_imovel.drop_duplicates(subset='Link')

# Função para limpar e converter colunas numéricas
def limpar_conversao_numerica(coluna):
    return pd.to_numeric(coluna.str.replace(r'\D', '', regex=True), errors='coerce')

# Aplicar função de limpeza nas colunas numéricas
df_imovel['Preço'] = limpar_conversao_numerica(df_imovel['Preço'])
df_imovel['Área'] = limpar_conversao_numerica(df_imovel['Área'])
df_imovel['Quartos'] = limpar_conversao_numerica(df_imovel['Quartos'])
df_imovel['Vagas'] = limpar_conversao_numerica(df_imovel['Vagas'])

# Remover imóveis sem preço ou área
df_imovel = df_imovel.dropna(subset=['Preço', 'Área'])

# Adicionar coluna M2
df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Área']

# Exibir DataFrame final
print(df_imovel)

# Salvar DataFrame em um arquivo Excel
df_imovel.to_excel('loft_imoveis.xlsx', index=False)
print(resposta)
