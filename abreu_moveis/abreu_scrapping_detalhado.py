from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

# Definir a variável de reorganização de colunas
reorganizar_colunas = True  # Defina como True se desejar reorganizar as colunas

# Configurar o Selenium
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Executar o navegador em modo headless (sem interface gráfica)

# Bloquear recursos de terceiros
prefs = {
    "profile.managed_default_content_settings.images": 2,
    "profile.managed_default_content_settings.stylesheets": 2,
    "profile.managed_default_content_settings.cookies": 2,
    "profile.managed_default_content_settings.javascript": 1,  # Ativar JavaScript apenas para funcionalidade essencial
    "profile.managed_default_content_settings.plugins": 2,
    "profile.managed_default_content_settings.popups": 2,
    "profile.managed_default_content_settings.geolocation": 2,
    "profile.managed_default_content_settings.notifications": 2,
    "profile.managed_default_content_settings.media_stream": 2,
}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# URL do site
url = "https://abreuimoveis.com.br/venda/residencial_comercial/natal/"
driver.get(url)

# Variável para selecionar quantos imóveis deseja extrair
NUM_IMOVEIS = 1112

# Emular a rolagem da página e coletar os dados
imoveis_extraidos = 0
dados_imoveis = []
codigos_imoveis = set()
caracteristicas_unicas = set()
infraestrutura_unicas = set()
imoveis_anteriores = 0
tentativas_sem_novos_imoveis = 0

# Primeiro passo: Extrair dados básicos dos imóveis
print("Extraindo dados básicos dos imóveis...")
with tqdm(total=NUM_IMOVEIS, desc="Imóveis extraídos", unit="imóvel") as pbar:
    while imoveis_extraidos < NUM_IMOVEIS and tentativas_sem_novos_imoveis < 20:
        try:
            # Rolar a página com ActionChains
            element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".col-xs-12.clb-search-result-property"))
            )
            actions = ActionChains(driver)
            actions.move_to_element(element).click().send_keys(Keys.PAGE_DOWN).perform()

            # Esperar o carregamento da nova parte da página de forma explícita
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".col-xs-12.clb-search-result-property"))
            )

            # Analisar o HTML carregado com BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Encontrar os imóveis
            imoveis = soup.find('div', id='imovel-boxes').find_all('div', class_='col-xs-12 imovel-box-single')

            # Verificar se novos imóveis foram carregados
            if len(imoveis) == imoveis_anteriores:
                tentativas_sem_novos_imoveis += 1
                print("Nenhum novo imóvel carregado. Tentativa:", tentativas_sem_novos_imoveis)
                continue
            else:
                tentativas_sem_novos_imoveis = 0
                imoveis_anteriores = len(imoveis)

            for imovel in imoveis:
                if imoveis_extraidos >= NUM_IMOVEIS:
                    break

                try:
                    # Extrair dados do imóvel
                    titulo_element = imovel.find('div', class_='titulo-anuncio')
                    link = titulo_element.find('a', href=True)['href'] if titulo_element.find('a', href=True) else ''
                    titulo = titulo_element.find('h2', class_='titulo-grid').text.strip() if titulo_element.find('h2', class_='titulo-grid') else ''
                    endereco = titulo_element.find('h3', itemprop='streetAddress').text.strip() if titulo_element.find('h3', itemprop='streetAddress') else ''
                    codigo = titulo_element.find('p').text.split(':')[-1].strip() if titulo_element.find('p') else '0'

                    # Verificar se o imóvel já foi extraído
                    if codigo in codigos_imoveis:
                        continue
                    else:
                        codigos_imoveis.add(codigo)

                    valores_element = imovel.find('div', class_='valores-grid')
                    preco = valores_element.find('span', class_='thumb-price').text if valores_element.find('span', class_='thumb-price') else '0'
                    condominio = valores_element.find('span', class_='item-price-condominio').text if valores_element.find('span', class_='item-price-condominio') else '0'
                    iptu = valores_element.find('span', class_='item-price-iptu').text if valores_element.find('span', class_='item-price-iptu') else '0'

                    # Inicializar valores padrões
                    dormitorios, suites, vagas, area = '0', '0', '0', '0'

                    amenities_element = imovel.find('div', class_='property-amenities amenities-main')
                    amenities = amenities_element.find_all('div')

                    for amenity in amenities:
                        small_text = amenity.find('small').text if amenity.find('small') else ''
                        value = amenity.find('span').text if amenity.find('span') else '0'
                        if small_text == 'Quartos':
                            dormitorios = value.strip()
                        elif small_text == 'Suítes':
                            suites = value.strip()
                        elif small_text == 'Vaga':
                            vagas = value.strip()
                        elif small_text == 'Privat.':
                            area = value.replace('m²', '').strip()

                    dados_imoveis.append({
                        "Título": titulo,
                        "Link": link,
                        "Endereço": endereco,
                        "Código": codigo,
                        "Preço": preco,
                        "Condomínio": condominio,
                        "IPTU": iptu,
                        "Dormitórios": dormitorios,
                        "Suítes": suites,
                        "Vagas": vagas,
                        "Área": area
                    })
                    imoveis_extraidos += 1
                    pbar.update(1)

                except Exception as e:
                    print(f"Erro ao processar imóvel: {e}")
                    continue

        except Exception as e:
            print(f"Erro ao rolar a página ou carregar novos imóveis: {e}")
            break

# Segundo passo: Extrair informações adicionais de cada imóvel
print("Extraindo informações adicionais dos imóveis...")
with tqdm(total=len(dados_imoveis), desc="Imóveis processados", unit="imóvel") as pbar:
    for imovel in dados_imoveis:
        try:
            # Acessar a página do imóvel
            driver.get(imovel["Link"])
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'body'))
            )
            soup_imovel = BeautifulSoup(driver.page_source, 'html.parser')

            # Extrair informações adicionais
            visualizacoes_element = soup_imovel.find('div', id='amenity-view-counter')
            visualizacoes = visualizacoes_element.find('span').text.strip() if visualizacoes_element else '0'
            banheiros_element = soup_imovel.find('div', id='amenity-banheiros')
            banheiros = banheiros_element.find('span').text.strip() if banheiros_element else '0'

            # Extrair características adicionais do imóvel
            caracteristicas_element = soup_imovel.find('div', class_='col-xs-12 col-sm-12 col-md-7 col-lg-8 clb-carac-imo')
            caracteristicas = [carac.text.strip() for carac in caracteristicas_element.find_all('p')] if caracteristicas_element else []
            caracteristicas_unicas.update(caracteristicas)

            # Extrair infraestrutura do imóvel
            infraestrutura_element = soup_imovel.find('div', class_='col-xs-12 col-sm-12 col-md-7 col-lg-8 clb-infra-imo')
            infraestrutura = [infra.text.strip() for infra in infraestrutura_element.find_all('p')] if infraestrutura_element else []
            infraestrutura_unicas.update(infraestrutura)

            # Adicionar informações adicionais ao dicionário do imóvel
            imovel["Banheiros"] = banheiros
            imovel["Visualizações"] = visualizacoes
            imovel["Características"] = caracteristicas
            imovel["Infraestrutura"] = infraestrutura

            pbar.update(1)

        except Exception as e:
            print(f"Erro ao acessar informações adicionais do imóvel: {e}")
            continue

# Fechar o navegador
driver.quit()

# Criar um DataFrame com os dados
df = pd.DataFrame(dados_imoveis)

# Função para limpar e converter colunas numéricas
def limpar_e_converter_coluna(coluna):
    return pd.to_numeric(df[coluna].str.replace(r'\D', '', regex=True), errors='coerce')

# Aplicar a função de limpeza e conversão nas colunas específicas
colunas_numericas = ["Código", "Preço", "Condomínio", "IPTU", "Dormitórios", "Suítes", "Vagas", "Área", "Banheiros", "Visualizações"]
for coluna in colunas_numericas:
    df[coluna] = limpar_e_converter_coluna(coluna)

# Remover linhas com valores nulos ou zero na coluna Área
df = df.dropna(subset=["Área"])
df = df[df["Área"] != 0]

# Remover linhas com valores nulos ou zero na coluna Preço
df = df.dropna(subset=["Preço"])
df = df[df["Preço"] != 0]

def separar_endereco(endereco):
    partes = endereco.split(',')
    rua = partes[0].strip() if len(partes) > 0 else ''
    resto = partes[1].strip() if len(partes) > 1 else ''
    bairro = resto.split(' - ')[0].strip() if ' - ' in resto else resto
    cidade_estado = resto.split(' - ')[1].strip() if ' - ' in resto else ''
    cidade = cidade_estado.split('/')[0].strip() if '/' in cidade_estado else cidade_estado
    estado = cidade_estado.split('/')[1].strip() if '/' in cidade_estado else ''
    return pd.Series([rua, bairro, cidade, estado.upper()])

df[['Rua', 'Bairro', 'Cidade', 'Estado']] = df['Endereço'].apply(separar_endereco)

# Unir características e infraestrutura
caracteristicas_e_infraestrutura_unicas = list(caracteristicas_unicas.union(infraestrutura_unicas))

# Criar colunas para cada característica e infraestrutura, preenchendo com 0
for item in caracteristicas_e_infraestrutura_unicas:
    df[item] = 0

# Preencher colunas com 1 para as características e infraestruturas presentes
for index, row in df.iterrows():
    for item in row['Características']:
        if item in df.columns:
            df.at[index, item] = 1
    for item in row['Infraestrutura']:
        if item in df.columns:
            df.at[index, item] = 1

# Remover colunas de Características e Infraestrutura originais
df = df.drop(columns=["Características", "Infraestrutura"])

# Reorganizar colunas se a variável estiver definida como True
if reorganizar_colunas:
    colunas_principais = ["Título", "Link", "Rua", "Bairro", "Cidade", "Estado", "Código", "Preço", "Área", "Condomínio", "IPTU", "Dormitórios", "Suítes", "Banheiros", "Vagas", "Visualizações"]
    colunas_finais = colunas_principais + caracteristicas_e_infraestrutura_unicas
    df = df[colunas_finais]

# Salvar os dados em um arquivo Excel
df.to_excel(r"C:\Users\galva\OneDrive\Documentos\GitHub\web-scrapping-com-python\base_de_dados_excel\abreu_moveis_data_base\imoveis_nordeste_venda_natal.xlsx", index=False)

print("Dados salvos em imoveis_nordeste_teste.xlsx")
