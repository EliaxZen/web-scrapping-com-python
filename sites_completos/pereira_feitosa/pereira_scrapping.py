from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging
import pandas as pd
import re

# Configuração do logging
logging.basicConfig(level=logging.INFO)

# Configurar o WebDriver utilizando o WebDriver Manager
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Para rodar o navegador em modo headless
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# URL do site
url = "https://www.pereirafeitosa.com.br/imoveis/a-venda"
driver.get(url)
logging.info("Página carregada.")

# Fechar mensagem de cookies se existir
try:
    cookies_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.btn.btn-success'))
    )
    cookies_button.click()
    logging.info("Mensagem de cookies fechada.")
except Exception as e:
    logging.error(f"Erro ao fechar a mensagem de cookies: {e}")

# Lista para armazenar os dados dos imóveis
dados_imoveis = []

# Função para limpar valores numéricos
def limpar_valor(valor):
    if valor:
        valor_limpo = re.sub(r'\D', '', valor)
        return int(valor_limpo) if valor_limpo else 0
    return 0

# Função para extrair dados dos imóveis e adicionar ao DataFrame
def extrair_dados_e_adicionar(dados_imoveis):
    imoveis = driver.find_elements(By.CSS_SELECTOR, 'div.card.card-listing')
    for imovel in imoveis:
        try:
            link = imovel.find_element(By.CSS_SELECTOR, 'a[href]').get_attribute('href')
            preco = imovel.find_element(By.CSS_SELECTOR, 'div.info-left p span.h-money').text.strip()
            titulo = imovel.find_element(By.CSS_SELECTOR, 'h2.card-title').text.strip()
            endereco = imovel.find_element(By.CSS_SELECTOR, 'h3.card-text').text.strip()
            descricao = imovel.find_element(By.CSS_SELECTOR, 'p.description.hidden-sm-down').text.strip()
            detalhes = imovel.find_elements(By.CSS_SELECTOR, 'div.values div.value p')

            # Inicializar variáveis com 0
            quartos = suites = banheiros = vagas = area = 0

            # Extrair detalhes baseado no texto ao lado do valor
            for detalhe in detalhes:
                valor = detalhe.find_element(By.CSS_SELECTOR, 'span.h-money').text.strip()
                nome = detalhe.text.split('\n')[1].strip().lower()

                if 'quartos' in nome:
                    quartos = limpar_valor(valor)
                elif 'suítes' in nome:
                    suites = limpar_valor(valor)
                elif 'banheiros' in nome:
                    banheiros = limpar_valor(valor)
                elif 'vagas' in nome:
                    vagas = limpar_valor(valor)
                elif 'm²' in nome:
                    area = limpar_valor(valor)

            preco = limpar_valor(preco)
            
            # Adicionar os dados extraídos à lista
            dados_imoveis.append({
                'Link': link,
                'Preço': preco,
                'Título': titulo,
                'Endereço': endereco,
                'Descrição': descricao,
                'Quartos': quartos,
                'Suítes': suites,
                'Banheiros': banheiros,
                'Vagas': vagas,
                'Área': area
            })
        except Exception as e:
            logging.error(f"Erro ao extrair dados do imóvel: {e}")

# Inicializar o DataFrame
df = pd.DataFrame()

# Esperar carregar os imóveis e clicar no botão 'Ver mais' até carregar todos
while True:
    try:
        # Aguardar que os imóveis sejam carregados
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.card.card-listing'))
        )
        num_imoveis_antes = len(driver.find_elements(By.CSS_SELECTOR, 'div.card.card-listing'))
        logging.info(f"Número de imóveis antes do clique: {num_imoveis_antes}")

        # Tentar clicar no botão 'Ver mais'
        ver_mais_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.btn.btn-md.btn-primary.btn-next'))
        )
        ver_mais_button.click()
        logging.info("Botão 'Ver mais' clicado.")
        
        # Esperar carregar os novos imóveis
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, 'div.card.card-listing')) > num_imoveis_antes
        )
        num_imoveis_depois = len(driver.find_elements(By.CSS_SELECTOR, 'div.card.card-listing'))
        logging.info(f"Novos imóveis carregados: {num_imoveis_depois}")

        # Extrair dados e adicionar ao DataFrame
        extrair_dados_e_adicionar(dados_imoveis)
        
        # Atualizar o DataFrame incrementando os novos dados
        df = pd.concat([df, pd.DataFrame(dados_imoveis)], ignore_index=True)

        # Se não carregar mais imóveis, sair do loop
        if num_imoveis_antes == num_imoveis_depois:
            break
    except Exception as e:
        logging.error(f"Erro ao clicar no botão 'Ver mais': {e}")
        break

# Fechar o WebDriver
driver.quit()

# Verificar se dados foram extraídos
if df.empty:
    logging.error("Nenhum imóvel foi encontrado ou extraído.")
else:
    # Remover imóveis com preço ou área iguais a 0, inexistentes, nulos ou vazios
    df = df[(df['Preço'] > 0) & (df['Área'] > 0)]

    # Preencher valores ausentes nas colunas numéricas com 0
    colunas_numericas = ['Preço', 'Quartos', 'Suítes', 'Banheiros', 'Vagas', 'Área']
    df[colunas_numericas] = df[colunas_numericas].fillna(0).astype(int)

    # Salvar os dados em um arquivo Excel
    df.to_excel('imoveis_pereira_feitosa.xlsx', index=False)
    logging.info("Dados salvos no arquivo 'imoveis_pereira_feitosa.xlsx'.")
