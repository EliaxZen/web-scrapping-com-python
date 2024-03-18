from selenium import webdriver

navegador = webdriver.Edge()

navegador.get('https://www.thaisimobiliaria.com.br/')

elemento = navegador.find_element_by_id('label-locality')

elemento.send_keys('brasilia')