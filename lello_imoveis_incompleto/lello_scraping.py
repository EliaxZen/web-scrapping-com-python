from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import random

# Lista de agentes de usuário
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
]

# Lista de proxies
proxy_list = [
    'http://proxy1:port',
    'http://proxy2:port',
    # Adicione mais proxies conforme necessário
]

# Configurar o driver do Selenium
service = ChromeService(executable_path=ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Executar em modo headless
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-blink-features=AutomationControlled')  # Desabilitar controle de automação do Blink
options.add_argument(f'user-agent={random.choice(user_agents)}')
options.add_argument(f'--proxy-server={random.choice(proxy_list)}')  # Adicionar proxy

# Evitar detecção como bot
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(service=service, options=options)
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

lista_de_imoveis = []
links_processados = set()

for pagina in range(1, 10):
    print(f'Processando página: {pagina}')
    url = f'https://www.zapimoveis.com.br/venda/imoveis/df+brasilia/?__ab=exp-aa-test:control,novopos:control,super-high:new,olx:control,score-rkg:sc-rkg&transacao=venda&onde=,Distrito%20Federal,Bras%C3%ADlia,,,,,city,BR%3EDistrito%20Federal%3ENULL%3EBrasilia,-15.826691,-47.92182,&pagina={pagina}'
    
    driver.get(url)
    
    time.sleep(random.uniform(5, 15))
    
    conteudo = driver.page_source
    site = BeautifulSoup(conteudo, 'html.parser')
    
    # Verificar se a página carregou corretamente
    if not site:
        print(f"Falha ao carregar a página {pagina}")
        continue
    
    # Imprimir o conteúdo HTML da página para análise
    print(f"Conteúdo HTML da página {pagina}:")
    print(site.prettify()[:2000])  # Imprimir apenas os primeiros 2000 caracteres para evitar excesso de saída
    
    imoveis = site.findAll('a', class_='result-card')
    
    # Verificar se a lista de imóveis foi encontrada
    print(f"Número de imóveis encontrados na página {pagina}: {len(imoveis)}")
    
    for imovel in imoveis:
        try:
            # Link do imóvel
            link = 'https://www.zapimoveis.com.br' + imovel.get('href')

            # Verificar se o link já foi processado
            if link in links_processados:
                continue

            # Verificar se cada elemento existe antes de acessá-lo
            titulo_elem = imovel.find('h3', attrs={'itemprop': 'streetAddress'})
            subtitulo_elem = imovel.find('span', attrs={'itemprop': 'addressLocality'})
            tipo_imovel_elem = imovel.find('div', attrs={'mb-2 card-title h5'})
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
df_imovel = pd.DataFrame(lista_de_imoveis, columns=['Título', 'Subtítulo', 'Link', 'Preço', 'Área', 'Quartos', 'Banheiros', 'Vagas'])

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
df_imovel['Vagas'] = limpar_conversao_numerica(df_imovel['Vagas'])

# Remover imóveis sem preço ou área
df_imovel = df_imovel.dropna(subset=['Preço', 'Área'])

# Adicionar coluna M2
df_imovel['M2'] = df_imovel['Preço'] / df_imovel['Área']

# Exibir DataFrame final
print(df_imovel)

# Salvar DataFrame em um arquivo Excel
df_imovel.to_excel('lello_imoveis.xlsx', index=False)

# Encerrar o driver do Selenium
driver.quit()
