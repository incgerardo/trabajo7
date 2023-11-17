# Importación de librerías necesarias
import re
import json
import time
import requests
import pandas as pd

from tqdm import tqdm
from datetime import datetime
from bs4 import BeautifulSoup
from multiprocessing.dummy import Pool as ThreadPool
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from pyshadow.main import Shadow

# Obtener la fecha y hora actual
now = datetime.now()
time_now = now.strftime("%d/%m/%Y %H:%M:%S")

# Leer un archivo CSV con datos de SKU
getcsv = pd.read_csv("sku1.csv").to_dict("records")
allcsv = [tt['sku'] for tt in getcsv]

# Configuración de variables de idioma para la URL
c1, c2 = "es", "es"
urls = [f"https://www.se.com/{c1}/{c2}/product/{gg}" for gg in allcsv]
alldata = []

# Configuración de opciones del navegador Chrome
chrome_options = webdriver.ChromeOptions()

# Inicialización del controlador de Chrome
driver = webdriver.Chrome(service=Service('chromedriver.exe'), options=chrome_options)

# Función para obtener el HTML de una URL usando Selenium y Pyshadow
def get_html(link):
    global driver
    html_result = ""
    shadow = Shadow(driver)
    driver.get(link)
    shadow.wait_for_page_loaded()
    shadow.set_explicit_wait(100, 100)
    description_html = shadow.find_element(".main-product-info.sc-pes-main-product-info").get_attribute("innerHTML")
    html_result += description_html
    specs = shadow.find_elements(".specifications-table")
    if not specs:
        time.sleep(3)
        specs = shadow.find_elements(".specifications-table")
    for spec in specs:
        html_result += spec.get_attribute("outerHTML")
    return html_result

# Función para obtener información de múltiples URLs
def get_info():
    print("Downloading HTML. Please wait... ")
    d = {}
    global urls
    for x in urls:
        id_ = x.split("/")[-1]
        try:
            d[id_] = get_html(x)
        except:
            continue
    return d

# Obtener HTML de las URLs
html_info = get_info()

# Lista de imágenes prohibidas
banned_images = ["https://www.se.com/mx/shop-static/assets/images/brand/premium.svg", ...]  # Lista completa de URLs

# Función para registrar información en un archivo de registro
def log(sku, message):
    with open("log.txt", "a") as f:
        f.write(f"{time_now}\nSKU:{sku}\n{message}\n-------------------\n")

# Función para extraer y parsear información de HTML usando BeautifulSoup
def parse(html, url):
    makedict = {}
    makesoup = BeautifulSoup(html, "lxml")
    sku = url.split("/")[-1]
    title = makesoup.find("h1", {"class": "main-product-info__description sc-pes-main-product-info"})
    # Extracción de información específica de la página

    # ... (código de extracción de datos)

    return makedict

# Función para realizar el scraping de la información
def scraping(url):
    req = requests.get(url)
    req.encoding = "utf-8"
    getdata = parse(req.text, url)
    alldata.append(getdata)

# Finalización del driver de Selenium
driver.quit()

# Uso de ThreadPool para el scraping paralelo de múltiples URLs
with ThreadPool(30) as pool:
    results = list(tqdm(pool.imap_unordered(scraping, urls), total=len(urls)))

# Creación de un DataFrame de pandas a partir de los datos recolectados
df = pd.DataFrame(alldata)

# Exportar los datos recolectados a un archivo CSV
df.to_csv("data1.csv", index=False, encoding="utf-8-sig")
