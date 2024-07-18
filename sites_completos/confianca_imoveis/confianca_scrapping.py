from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import re

# Configurar opções do Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")  # Executar em modo headless (sem interface gráfica)
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# Configurar o driver do Chrome
service = ChromeService(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# URL base com a variável de paginação
base_url = "https://confiancaimoveisrs.com.br/imoveis/venda/canoas/-/-/-?filtros&min=0&max=8790898&ordem=desc-valor&pagination={}"

# Quantidade máxima de páginas para scraping
max_pages = 78

# Lista para armazenar dados extraídos
imoveis = []

# Função para limpar dados numéricos
def limpar_dados(dado):
    return re.sub(r'\D', '', dado)  # Remove todos os caracteres não numéricos

# Função para extrair informações de um imóvel
def extrair_info(imovel):
    try:
        link_tag = imovel.find_element(By.TAG_NAME, 'a')
        link = "https://confiancaimoveisrs.com.br" + link_tag.get_attribute('href') if link_tag else None

        preco_tag = imovel.find_element(By.CLASS_NAME, 'CardApartament_price__K_2Hc')
        preco = limpar_dados(preco_tag.text.strip().replace("Venda: ", "")) if preco_tag else None

        tipo_imovel_tag = imovel.find_element(By.CLASS_NAME, 'CardApartament_txt__GzqRq')
        tipo_imovel = tipo_imovel_tag.text.strip() if tipo_imovel_tag else None

        endereco_tag = imovel.find_element(By.CLASS_NAME, 'CardApartament_address__kQXZ9')
        endereco = endereco_tag.text.strip() if endereco_tag else None

        detalhes = imovel.find_elements(By.CLASS_NAME, 'CardApartament_adjust_icons__ICKoT')

        quartos = suites = banheiros = vagas = area = 0
        for detalhe in detalhes:
            titulo_detalhe = detalhe.get_attribute('title')
            valor_detalhe_tag = detalhe.find_element(By.CLASS_NAME, 'CardApartament_margin__fwTb6')
            valor_detalhe = valor_detalhe_tag.text.strip() if valor_detalhe_tag else ""

            try:
                if "Dormitórios" in titulo_detalhe:
                    quartos_suites = re.findall(r'\d+', valor_detalhe)  # Encontra todos os números
                    quartos = int(quartos_suites[0]) if quartos_suites else 0
                    suites = int(quartos_suites[1]) if len(quartos_suites) > 1 else 0
                elif "Banheiros" in titulo_detalhe:
                    banheiros = int(limpar_dados(valor_detalhe))
                elif "vagas" in titulo_detalhe.lower():
                    vagas = int(limpar_dados(valor_detalhe))
                elif "Área" in titulo_detalhe:
                    area = limpar_dados(valor_detalhe)
            except (IndexError, ValueError):
                print(f"Erro ao processar detalhe: {titulo_detalhe}, {valor_detalhe}")

        return {
            'Link': link,
            'Preco': preco,
            'Tipo_imovel': tipo_imovel,
            'Endereco': endereco,
            'Quartos': quartos,
            'Suites': suites,
            'Vagas': vagas,
            'Banheiros': banheiros,
            'Area': area
        }
    except Exception as e:
        print(f"Erro ao extrair informações: {e}")
        return None

# Função principal de scraping
def scrape_vogelhaus(pages):
    for page in range(1, pages + 1):
        print(f"Scraping página {page}...")
        try:
            driver.get(base_url.format(page))
            time.sleep(3)  # Espera para garantir que a página carregue completamente

            # Selecionando todos os cards de imóveis
            imoveis_divs = driver.find_elements(By.CLASS_NAME, 'ListPiecesProperties_card__a5gsY')
            print(f"Número de imóveis encontrados na página {page}: {len(imoveis_divs)}")

            for imovel in imoveis_divs:
                info = extrair_info(imovel)
                if info:
                    imoveis.append(info)

            # Pausa para evitar sobrecarga no servidor
            time.sleep(2)

        except Exception as e:
            print(f"Erro ao acessar a página {page}: {e}")
            break

# Executando o scraping
scrape_vogelhaus(max_pages)

# Fechar o driver
driver.quit()

# Verificando se a lista de imóveis contém dados
if imoveis:
    # Convertendo a lista de imóveis para um DataFrame do pandas
    df = pd.DataFrame(imoveis)

    # Convertendo colunas numéricas para inteiros ou floats
    df['Preco'] = pd.to_numeric(df['Preco'], errors='coerce')
    df['Quartos'] = pd.to_numeric(df['Quartos'], errors='coerce')
    df['Suites'] = pd.to_numeric(df['Suites'], errors='coerce')
    df['Vagas'] = pd.to_numeric(df['Vagas'], errors='coerce')
    df['Banheiros'] = pd.to_numeric(df['Banheiros'], errors='coerce')
    df['Area'] = pd.to_numeric(df['Area'], errors='coerce')

    # Removendo linhas onde Preco ou Area sejam 0, nulos ou vazios
    df = df.dropna(subset=['Preco', 'Area'])
    df = df[(df['Preco'] != 0) & (df['Area'] != 0)]

    # Adicionar nova coluna 'M2' e calcular a divisão
    df['M2'] = df['Preco'] / df['Area']
    
    # Salvando os dados em um arquivo Excel
    df.to_excel('Imoveis_confianca.xlsx', index=False)
    print("Dados salvos em 'Imoveis_Vogelhaus.xlsx'")
else:
    print("Nenhum dado foi extraído.")
