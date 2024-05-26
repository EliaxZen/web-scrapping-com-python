import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from selenium.common.exceptions import StaleElementReferenceException


# Configuração do Selenium com Chrome e WebDriver Manager
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

lista_de_imoveis = []

# URL do site
driver.get('https://refugiosurbanos.com.br/imoveis')

# Defina o número de vezes que deseja clicar no botão "Carregar mais imóveis"
num_clicar_carregar_mais = 3

# Função para clicar no botão de carregar mais imóveis
def carregar_mais_imoveis(driver, num_clicks):
    for _ in range(num_clicks):
        try:
            # Execute um script JavaScript para rolar a página para baixo
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Espere um pouco para os imóveis serem carregados
        except Exception as e:
            print("Não foi possível carregar mais imóveis:", e)
            break

# Clicar no botão de "Carregar mais imóveis" um número específico de vezes
carregar_mais_imoveis(driver, num_clicar_carregar_mais)

# Loop para extrair informações de todos os imóveis
while True:
    # Aguarde até que os imóveis estejam visíveis
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.imovel"))
    )
    imoveis = driver.find_elements(By.CSS_SELECTOR, "article.imovel")

    for imovel in imoveis:
        try:
            link_element = imovel.find_element(By.CSS_SELECTOR, "a[target='_blank']")
            link_imovel = link_element.get_attribute('href')
        except StaleElementReferenceException:
            print("O elemento do link do imóvel se tornou obsoleto. Tentando novamente...")
            continue  # Continue para a próxima iteração do loop
        driver.get(link_imovel)
        # Agora você está na página de detalhes do imóvel e pode extrair as informações
        page_content = driver.page_source
        site = BeautifulSoup(page_content, "html.parser")

        # Extraindo o título
        titulo = site.find('h1', class_='titulo_pagina no-border').get_text(strip=True)

        # Extraindo informações do artigo com detalhes do imóvel
        detalhes_imovel = site.find('article', id='detalhes_imovel')

        # Extraindo o subtítulo e descrição
        descricao_imovel = site.find('article', id='descricao_imovel')
        subtitulo = descricao_imovel.find('h4').get_text(strip=True)
        descricao = ' '.join([p.get_text(strip=True) for p in descricao_imovel.find_all('p')])

        # Função para extrair informações das tags <h2> e <p>
        def extrair_informacoes(detalhes_imovel):
            infos = {}
            current_header = ''
            for element in detalhes_imovel.find_all(['h2', 'p']):
                if element.name == 'h2':
                    current_header = element.get_text(strip=True)
                elif element.name == 'p' and current_header:
                    infos[current_header] = element.get_text(strip=True)
            return infos

        # Extraindo informações detalhadas
        informacoes = extrair_informacoes(detalhes_imovel)

        # Extraindo informações detalhadas
        configuracao = informacoes.get('Configuração')
        
        area_util_split = configuracao.split('Área útil: ')
        area_util = area_util_split[1].split('\n')[0].strip() if len(area_util_split) > 1 else None

        quartos_split = configuracao.split('Quartos')
        quartos = quartos_split[0].split()[-1].strip() if len(quartos_split) > 1 else None

        suite_split = configuracao.split('Suíte')
        suite = suite_split[0].split()[-1].strip() if len(suite_split) > 1 else None

        banheiros_split = configuracao.split('Banheiros')
        banheiros = banheiros_split[0].split()[-1].strip() if len(banheiros_split) > 1 else None

        vaga_split = configuracao.split('Vaga')
        vaga = vaga_split[0].split()[-1].strip() if len(vaga_split) > 1 else None

        # Organizando as informações no dicionário
        data = {
            'Título': titulo,
            'Subtítulo': subtitulo,
            'Descrição': descricao,
            'Bairro': informacoes.get('Bairro'),
            'Área': area_util,
            'Quartos': quartos,
            'Suíte': suite,
            'Banheiros': banheiros,
            'Vaga': vaga,
            'Detalhes': informacoes.get('Detalhes'),
            'Preço': informacoes.get('Valores').split('Preço: ')[1].split('\n')[0].strip(),
            'Condomínio': informacoes.get('Valores').split('Condomínio: ')[1].split('<')[0].strip(),
            'IPTU': informacoes.get('Valores').split('IPTU: ')[1].strip(),
            'Código RU': informacoes.get('Código RU')
        }

        # Adicione as informações extraídas à lista_de_imoveis
        lista_de_imoveis.append(data)

        # Volte para a página principal com a lista de imóveis
        driver.back()

    # Verifique se existe um botão para carregar mais imóveis e clique nele
    try:
        carregar_mais_imoveis(driver)
    except Exception as e:
        print("Todos os imóveis foram carregados ou ocorreu um erro:", e)
        break

# Feche o navegador
driver.quit()

# Converta a lista_de_imoveis em um DataFrame
df_imoveis = pd.DataFrame(lista_de_imoveis)

# Salvar o DataFrame em um arquivo Excel
nome_arquivo = 'lista_de_imoveis.xlsx'
df_imoveis.to_excel(nome_arquivo, index=False)

print(f'Os dados foram salvos com sucesso no arquivo {nome_arquivo}.')