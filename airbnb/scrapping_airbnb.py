from time import sleep
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

driver_path = ChromeDriverManager().install()

# Create a service object with the driver path
service = Service(driver_path)

navegador = webdriver.Chrome(service=service)

navegador.get('https://www.airbnb.com.br/s/Brasilia--Bras%C3%ADlia-~-Federal-District--Brazil/homes?tab_id=home_tab&refinement_paths%5B%5D=%2Fhomes&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2024-04-01&monthly_length=3&monthly_end_date=2024-07-01&price_filter_input_type=0&channel=EXPLORE&query=Brasilia%2C%20Bras%C3%ADlia%20-%20Federal%20District&place_id=ChIJMY_byXY3WpMRrGc50eIQKSk&date_picker_type=calendar&source=structured_search_input_header&search_type=autocomplete_click')

sleep(2)

input_place = navegador.find_element(By.CSS_SELECTOR, 'a')
print(input_place['href'])

navegador.quit()



