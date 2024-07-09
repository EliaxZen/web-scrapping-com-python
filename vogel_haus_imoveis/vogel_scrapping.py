import requests
from bs4 import BeautifulSoup
import time
import pandas as pd

# Definindo a URL base com a variável de paginação
base_url = "https://www.vogelhausimoveis.com.br/imoveis/venda/canoas/-/-/-?filtros&min=0&max=8500000&ordem=desc-valor&pagination={}"

# Criando uma sessão de requests
session = requests.Session()

# Definindo a quantidade máxima de páginas para scraping (ajustar conforme necessário)
max_pages = 5

# Lista para armazenar dados extraídos
imoveis = []

# Função para limpar dados
def limpar_dados(dado):
    return dado.replace('m²', '').strip()

# Função para extrair informações de um imóvel
def extrair_info(imovel):
    try:
        link_tag = imovel.find('a', target='_blank')
        if link_tag:
            link = "https://www.vogelhausimoveis.com.br" + link_tag['href']
        else:
            link = None
            print("Link não encontrado")

        preco_tag = imovel.select_one('.CardApartament_price__K_2Hc')
        if preco_tag:
            preco = preco_tag.text.strip()
        else:
            preco = None
            print("Preço não encontrado")

        tipo_imovel_tag = imovel.select_one('.CardApartament_txt__GzqRq')
        if tipo_imovel_tag:
            tipo_imovel = tipo_imovel_tag.text.strip()
        else:
            tipo_imovel = None
            print("Tipo de imóvel não encontrado")

        endereco_tag = imovel.select_one('.CardApartament_address__kQXZ9')
        if endereco_tag:
            endereco = endereco_tag.text.strip()
        else:
            endereco = None
            print("Endereço não encontrado")

        detalhes = imovel.find_all('li', class_='CardApartament_adjust_icons__ICKoT')

        quarto = suite = banheiro = vaga = area = 0
        for detalhe in detalhes:
            titulo_detalhe = detalhe.get('title', '')
            valor_detalhe_tag = detalhe.find('div', class_='CardApartament_margin__fwTb6')
            if valor_detalhe_tag:
                valor_detalhe = valor_detalhe_tag.get_text(strip=True)
            else:
                valor_detalhe = ""
                print("Valor do detalhe não encontrado")

            try:
                if "Dormitórios" in titulo_detalhe:
                    quarto = int(valor_detalhe.split(' ')[0])
                    suite = int(valor_detalhe.split(' ')[2].replace('Suítes', '').strip())
                elif "Banheiros" in titulo_detalhe:
                    banheiro = int(valor_detalhe.split(' ')[0])
                elif "Vagas" in titulo_detalhe:
                    vaga = int(valor_detalhe.split(' ')[0])
                elif "Área" in titulo_detalhe:
                    area = limpar_dados(valor_detalhe)
            except (IndexError, ValueError):
                print(f"Erro ao processar detalhe: {titulo_detalhe}, {valor_detalhe}")

        return {
            'link': link,
            'preco': preco,
            'tipo_imovel': tipo_imovel,
            'endereco': endereco,
            'quartos': quarto,
            'suites': suite,
            'vagas': vaga,
            'banheiros': banheiro,
            'area': area
        }
    except Exception as e:
        print(f"Erro ao extrair informações: {e}")
        return None

# Função principal de scraping
def scrape_vogelhaus(pages):
    for page in range(1, pages + 1):
        print(f"Scraping página {page}...")
        try:
            response = session.get(base_url.format(page))
            response.raise_for_status()  # Verifica se a requisição foi bem-sucedida
            soup = BeautifulSoup(response.content, 'html.parser')

            # Selecionando todos os cards de imóveis
            imoveis_divs = soup.find_all('div', class_='ListPiecesProperties_card__a5gsY')
            print(f"Número de imóveis encontrados na página {page}: {len(imoveis_divs)}")

            for imovel in imoveis_divs:
                info = extrair_info(imovel)
                if info:
                    imoveis.append(info)

            # Pausa para evitar sobrecarga no servidor
            time.sleep(2)

        except requests.exceptions.RequestException as e:
            print(f"Erro ao acessar a página {page}: {e}")
            break

# Executando o scraping
scrape_vogelhaus(max_pages)

# Verificando se a lista de imóveis contém dados
if imoveis:
    # Convertendo a lista de imóveis para um DataFrame do pandas
    df = pd.DataFrame(imoveis)

    # Salvando os dados em um arquivo Excel
    df.to_excel('imoveis_vogelhaus.xlsx', index=False)
    print("Dados salvos em 'imoveis_vogelhaus.xlsx'")
else:
    print("Nenhum dado foi extraído.")
