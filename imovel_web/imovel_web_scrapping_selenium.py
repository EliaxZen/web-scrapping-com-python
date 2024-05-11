import time
import random
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# Função para extrair informações de um imóvel
def extrair_informacoes_imovel(driver, link, lista_de_imoveis):
    driver.get(link)
    time.sleep(random.uniform(1, 5))  # Pausa aleatória entre 1 e 5 segundos para simular comportamento humano
    
    try:
        # Verificar se o site pede confirmação de que não é um robô
        if "imovelweb.com.br" in driver.current_url:
            # Preencher o campo de resposta do desafio de verificação
            response_element = driver.find_element(By.ID, "cf-chl-widget-m6glx_response")
            response_element.send_keys("página segura")  # Substitua com uma resposta adequada

            # Clicar na caixa de verificação
            checkbox = driver.find_element(By.XPATH, "//div[@class='recaptcha-checkbox-checkmark']")
            actions = ActionChains(driver)
            actions.move_to_element(checkbox).click().perform()
            time.sleep(random.uniform(2, 4))  # Aguardar alguns segundos após clicar na caixa de verificação

        # Extrair informações do imóvel
        titulo_element = driver.find_element(By.XPATH, "/html/body/div[2]/main/div/div/article/div/section[2]/div[1]/h4")
        titulo = titulo_element.text.strip() if titulo_element else ""
        subtitulo_element = driver.find_element(By.XPATH, "//*[@id='article-container']/hgroup[2]/div/h1")
        subtitulo = subtitulo_element.text.strip() if subtitulo_element else ""
        preco_element = driver.find_element(By.XPATH, "//*[@id='article-container']/div[1]/div/div[1]/span[1]/span")
        preco = preco_element.text.strip() if preco_element else ""
        preco_condominio_element = driver.find_element(By.CLASS_NAME, "price-expenses")
        preco_condominio = preco_condominio_element.text.strip() if preco_condominio_element else ""
        descricao_element = driver.find_element(By.XPATH, "//*[@id='longDescription']/div")
        descricao = descricao_element.text.strip() if descricao_element else ""
        
        # Extrair tipo do imóvel e área
        tipo_e_area_element = driver.find_element(By.CLASS_NAME, "title-type-sup-property")
        tipo_e_area_text = tipo_e_area_element.text.strip() if tipo_e_area_element else ""
        tipo, area = tipo_e_area_text.split("·")[:2]
        tipo = tipo.strip() if tipo else ""
        area = area.strip() if area else ""
        
        # Extrair informações sobre quartos, banheiros, vagas, suítes e anos
        icon_features = driver.find_element(By.ID, "section-icon-features-property")
        icon_features_elements = icon_features.find_elements(By.CLASS_NAME, "icon-feature")
        quartos, banheiros, vagas, suites, anos = None, None, None, None, None
        for element in icon_features_elements:
            text = element.text.strip()
            if "quarto" in text.lower():
                quartos = text.split()[0]
            elif "banheiro" in text.lower():
                banheiros = text.split()[0]
            elif "vaga" in text.lower():
                vagas = text.split()[0]
            elif "suíte" in text.lower():
                suites = text.split()[0]
            elif "anos" in text.lower():
                anos = text.split()[0]
        
        # Extrair nome da imobiliária
        imobiliaria_element = driver.find_element(By.XPATH, "//*[@id='reactPublisherData']/div/div/div/h3")
        imobiliaria = imobiliaria_element.text.strip() if imobiliaria_element else ""
        
        # Adicionar informações à lista de imóveis
        lista_de_imoveis.append([titulo, subtitulo, tipo, area, preco, preco_condominio, descricao, imobiliaria, quartos, banheiros, vagas, suites, anos, link])
    except Exception as e:
        print(f"Erro ao extrair informações do imóvel: {e}")

def scrape_imoveis():
    opts = Options()
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")
    opts.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36")

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--memory-growth=10gb")
    chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )

    return driver

# Lista para armazenar os dados dos imóveis
lista_de_imoveis = []

# Usar um conjunto para armazenar os URLs dos imóveis já adicionados
urls_adicionados = set()

# Defina um intervalo de tempo mínimo e máximo para as pausas (em segundos)
# Tempo de espera entre solicitações (em segundos)
TEMPO_ESPERA = 0  # 1 segundo

# Configurar o driver
driver = scrape_imoveis()

for pagina in range(1, 395):
    print(f"Navegando na página {pagina}")
    url = f"https://www.imovelweb.com.br/imoveis-aluguel-distrito-federal-pagina-{pagina}.html"
    try:
        resposta = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        resposta.raise_for_status()  # Levanta um erro se a requisição falhar
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a página: {e}")
        continue

    conteudo = resposta.content
    site = BeautifulSoup(conteudo, "html.parser")
    # Modificado para encontrar os elementos corretos dos imóveis
    imoveis = site.findAll("h3", attrs={"data-qa": "POSTING_CARD_DESCRIPTION"})

    for imovel in imoveis:
        # Link do imóvel
        link = "https://www.imovelweb.com.br" + imovel.a["href"]

        # Verificar se o imóvel já foi adicionado
        if link in urls_adicionados:
            continue  # Se já foi adicionado, pule para o próximo imóvel

        # Adicionar o URL do imóvel à lista de URLs adicionados
        urls_adicionados.add(link)

        # Extrair informações detalhadas do imóvel usando o Selenium
        extrair_informacoes_imovel(driver, link, lista_de_imoveis)
        
    # Adicione um tempo de espera entre as solicitações
    time.sleep(TEMPO_ESPERA)

# Fechar o navegador após a coleta de dados
driver.quit()

# Criar DataFrame com os dados dos imóveis
df_imovel = pd.DataFrame(
    lista_de_imoveis,
    columns=["Título", "Subtítulo", "Tipo", "Área", "Preço", "Preço do Condominio", "Descrição", "Imobiliária", "Quartos", "Banheiros", "Vagas", "Suíte", "Anos", "Link"]
)

# Remova o prefixo "R$" e quaisquer caracteres não numéricos da coluna "Preço"
df_imovel["Preço"] = df_imovel["Preço"].str.replace(r"R\$", "").str.replace(r"\D", "", regex=True)

# Converte a coluna para valores numéricos
df_imovel["Preço"] = pd.to_numeric(df_imovel["Preço"])

# Remova caracteres não numéricos da coluna "Área", "Quartos", "Banheiros", "Vagas", "Suíte" e "Anos" e converta para valores numéricos
df_imovel["Área"] = df_imovel["Área"].str.extract(r"(\d+)").astype(float)
df_imovel["Quartos"] = df_imovel["Quartos"].str.extract(r"(\d+)").astype(float)
df_imovel["Banheiros"] = df_imovel["Banheiros"].str.extract(r"(\d+)").astype(float)
df_imovel["Vagas"] = df_imovel["Vagas"].str.extract(r"(\d+)").astype(float)
df_imovel["Suíte"] = df_imovel["Suíte"].str.extract(r"(\d+)").astype(float)
df_imovel["Anos"] = df_imovel["Anos"].str.extract(r"(\d+)").astype(float)

# Adicionar nova coluna 'M2' e calcular a divisão
df_imovel["M2"] = df_imovel["Preço"] / df_imovel["Área"]

# Salvar DataFrame em um arquivo Excel
df_imovel.to_excel("imoveis_df.xlsx", index=False)
