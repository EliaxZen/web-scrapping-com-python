import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from time import sleep


#options.add_argument('--headless')


navegador = webdriver.Edge()

navegador.get('https://www.thaisimobiliaria.com.br/')

sleep(1)

input_place = navegador.find_element_by_tag_name('input')
input_place.send_keys('São Paulo')
input_place.submit()


# site = BeautifulSoup(navegador.page_source, 'html.parser')

# print(site.prettify())








