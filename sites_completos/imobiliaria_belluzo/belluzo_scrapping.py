from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from tqdm import tqdm
import time

def scrape_data():
    # Configurações do WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://imobiliariabelluzzo.com.br/imovel?operacao=1&codigo=&tipoimovel=&imos_codigo=&empreendimento=&destaque=false&vlini=&vlfim=&exclusivo=false&cidade=&pais=&filtropais=false&order=maxval&limit=9&page=2&minhacasa=false")
    
    # Scroll down until all properties are loaded
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Aguardando o carregamento dos dados
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    # Extraindo os dados
    imoveis = driver.find_elements(By.CSS_SELECTOR, 'div[ng-repeat="op in imoveisRow"]')
    data = []

    for imovel in tqdm(imoveis, desc="Scraping properties"):
        retries = 3  # Tentativas de recuperar o elemento
        while retries > 0:
            try:
                # Verificações para garantir que nenhum elemento seja None
                titulo_elem = imovel.find_element(By.CSS_SELECTOR, 'h3 a')
                titulo = titulo_elem.text if titulo_elem else None
                
                link = titulo_elem.get_attribute('href') if titulo_elem else None

                codigo_elem = imovel.find_element(By.CSS_SELECTOR, 'span.imovel_cod')
                codigo = codigo_elem.text.split(": ")[1] if codigo_elem and len(codigo_elem.text.split(": ")) > 1 else None
                
                endereco_elem = imovel.find_element(By.CSS_SELECTOR, 'div.item_address')
                endereco = endereco_elem.text.split("\n") if endereco_elem else []
                
                preco_elem = imovel.find_element(By.CSS_SELECTOR, 'div.item_prices dd')
                preco = preco_elem.text.replace(".", "").replace(",", ".") if preco_elem else None
                
                endereco_dict = {"Avenida": None, "Bairro": None, "Cidade": None, "Lote": None, "Quadra": None}
                for info in endereco:
                    if "Av" in info or "Rua" in info:
                        endereco_dict["Avenida"] = info
                    elif "Bairro:" in info and len(info.split(": ")) > 1:
                        endereco_dict["Bairro"] = info.split(": ")[1]
                    elif "Cidade:" in info and len(info.split(": ")) > 1:
                        endereco_dict["Cidade"] = info.split(": ")[1]
                    elif "Lote:" in info and len(info.split(": ")) > 1:
                        endereco_dict["Lote"] = info.split(": ")[1]
                    elif "Quadra:" in info and len(info.split(": ")) > 1:
                        endereco_dict["Quadra"] = info.split(": ")[1]

                if preco and float(preco) > 0:
                    data.append({
                        "Título": titulo,
                        "Link": link,
                        "Código": codigo,
                        "Avenida": endereco_dict["Avenida"],
                        "Bairro": endereco_dict["Bairro"],
                        "Cidade": endereco_dict["Cidade"],
                        "Lote": endereco_dict["Lote"],
                        "Quadra": endereco_dict["Quadra"],
                        "Preço": preco
                    })
                break  # Se tudo foi bem, saia do loop de retries
            except Exception as e:
                retries -= 1
                if retries == 0:
                    print(f"Erro ao processar um imóvel: {e}")

    driver.quit()

    # Convertendo para DataFrame
    if data:  # Verifica se há dados antes de criar o DataFrame
        df = pd.DataFrame(data)
        
        # Exibindo dados coletados antes do filtro
        print("Dados coletados antes do filtro:")
        print(df)
        
        # Tratamento de dados
        df["Preço"] = pd.to_numeric(df["Preço"], errors='coerce')
        df["Código"] = pd.to_numeric(df["Código"], errors='coerce')
        df["Lote"] = pd.to_numeric(df["Lote"], errors='coerce')
        
        # Filtrar imóveis com preço válido
        df = df[df['Preço'] > 0]
        
        # Exibindo dados coletados após o filtro
        print("Dados coletados após o filtro:")
        print(df)
        
        # Salvando em Excel
        df.to_excel("imoveis_belluzo.xlsx", index=False)
    else:
        print("Nenhum dado foi coletado.")

if __name__ == "__main__":
    scrape_data()
