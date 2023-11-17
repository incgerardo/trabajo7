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

now = datetime.now()
time_now = now.strftime("%d/%m/%Y %H:%M:%S")
getcsv = pd.read_csv("sku1.csv").to_dict("records")
allcsv = [tt['sku'] for tt in getcsv]
c1,c2 = "es","es"  #REPLACE THIS TO c1,c2 = "es","es"
urls = [f"https://www.se.com/{c1}/{c2}/product/{gg}" for gg in allcsv]
alldata = []
chrome_options = webdriver.ChromeOptions()

#chrome_options.add_argument('--headless')
"""
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-web-security")
chrome_options.add_argument("--disable-site-isolation-trials")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
"""

driver = webdriver.Chrome(service=Service('chromedriver.exe'),options=chrome_options)
def get_html(link):
    global driver
    html_result = ""
    shadow = Shadow(driver)
    driver.get(link)
    shadow.wait_for_page_loaded()
    shadow.set_explicit_wait(100,100)
    description_html = shadow.find_element(".main-product-info.sc-pes-main-product-info").get_attribute("innerHTML")
    html_result += description_html
    specs = shadow.find_elements(".specifications-table")
    if bool(specs) == False:
        time.sleep(3)
        specs = shadow.find_elements(".specifications-table")
    for spec in specs:
        html_result += spec.get_attribute("outerHTML")
    return html_result

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

html_info = get_info()
banned_images = ["https://www.se.com/mx/shop-static/assets/images/brand/premium.svg","https://www.se.com/mx/shop-static/assets/images/brand/premium.svg&p_File_Type=rendition_1500_jpg", "https://www.se.com/fr/shop-static/assets/images/pdp-page/3d-icon.svg&p_File_Type=rendition_1500_jpg", "https://www.se.com/fr//shop-static/assets/images/pdp-page/dimension_icon.svg&p_File_Type=rendition_1500_jpg", "https://www.se.com/fr/shop-static/assets/images/pdp-page/3d-icon.svg&p_File_Type=rendition_1500_jpg", "https://www.se.com/mx/shop-static/assets/images/brand/NoImageAvailable.png&p_File_Type=rendition_1500_jpg", "https://www.se.com/us/shop-static/assets/images/brand/squared-logo-green.svg&p_File_Type=rendition_1500_jpg","https://www.se.com/us/shop-static/assets/images/brand/squared-logo-green.svg","https://www.se.com/fr/shop-static/assets/images/pdp-page/3d-icon.svg","https://www.se.com/fr//shop-static/assets/images/pdp-page/dimension_icon.svg","https://www.se.com/mx/shop-static/assets/images/brand/NoImageAvailable.png"]

def log(sku,message):
    with open("log.txt","a") as f:
        f.write(f"{time_now}\nSKU:{sku}\n{message}\n-------------------\n")


def parse(html, url,):
    makedict = {}
    makesoup = BeautifulSoup(html, "lxml")
    sku = url.split("/")[-1]
    title = makesoup.find("h1", {"class":"main-product-info__description sc-pes-main-product-info"})

    if title is not None:
        makedict['title'] = title.text.strip()
    makedict['sku'] = sku
    makedict['url'] = url
    price = makesoup.find("div", {"class":re.compile("price")})
    description = makesoup.find("div", {"class":"description__content"})
    if description is not None:
        makedict['description'] = description.get_text()

    if price is not None:
        makedict['price'] = price.text.split("USD")[0].strip().replace("P.V.R: ","").replace("Price*: ","")
    else:
        try:
            price = json.loads(makesoup.select_one("pes-product-main")["plain-cta-area"])["price"]
        except:
            message = "Price not found"
            log(sku,message)
    try:
        json_script_tag = makesoup.find(lambda tag: "el.assetBar" in tag.text)
        json_script = json_script_tag.text
        json_data = json.loads(json_script.split("el.assetBar = ")[-1].split(";el.productRelations")[0])
        documents = json_data.get("documents", [])
        product_data_sheet = ""
        for document in documents:
            if document.get("documentType") == "Product Data Sheet":
                product_data_sheet = document.get("url", "")

        makedict["Product Data Sheet"] = product_data_sheet
    except:
        message = "Product data sheet not found"
        log(sku,message)

    li = makesoup.find_all("li",{"class":re.compile("documents__list-item")})

    for tt in li:
        link = ""
        finda = tt.find("a").get("href")
        ol = tt.find("a").text.strip()
        if "https" not in str(finda) and "#" not in str(finda):
            link = f"https://www.se.com{finda}"
        elif "Documentos" in ol:
            link = f"https://www.traceparts.com/els/schneider-electric-ws/goto?PartNumber={sku}"
        else:
            link = finda
        makedict[ol +" file url"] = link

    finddiv = makesoup.find("div", {"class": re.compile("sc-pes-media-gallery")})
    images = []

    if finddiv is not None:
        findallsrc = finddiv.find_all("img")
        for tt1 in findallsrc:
            if "https" in tt1.get("src"):
                image = tt1.get("src")

                if not ".svg" in image:
                    image = image.split("&p_File_Type=renditio")[0]+"&p_File_Type=rendition_1500_jpg"
                if not image in banned_images:
                    images.append(image)
    try:
        product_media = makesoup.select_one("pes-product-main")["plain-product-media"]
        media_urls = [z.split("&p_File_Type")[0] for z in re.findall('(?<=").*?(?=")', product_media ) if "http" in z]
        svgs = list(set([z for z in media_urls if ".svg" in z]))
        images += svgs
        for image in images:
            for banned in banned_images:
                if image==banned:
                    images.remove(image)
        images = list(set(images))
    except:
        ...

    makedict["product images"] = ",".join(images)
    req = requests.get(f"https://www.se.com/{c1}/{c2}/product/api/media/{sku}")
    req.encoding = "utf-8"

    media_data = req.json()

    video = ""

    if media_data.get("videoGroups"):
        video_groups = media_data["videoGroups"]
        if video_groups:
            video_items = video_groups[0]["videoItems"]
            if video_items:
                video_url = video_items[0]["videoUrl"]
                video = video_url.replace("embed/","watch?v=") + "&t=1s"

    makedict["video"] = video

    try:
        find360 = html.split('&quot;image360Url&quot;:&quot;')[1].split('&quot;')[0]
        makedict['360 images'] = find360
    except:
        message =  "360 images not found"
        log(sku,message)

    char = makesoup.find("li",{"id":"characteristics"})

    if char is not None:
        findalltr = char.find_all("tr")
        for tt1 in findalltr:
            th = tt1.find("th")
            td = tt1.find("td")
            makedict[th.text.strip()] = td.text.strip()

    char = makesoup.find("li",{"id":"characteristics"})

    if char is not None:
        findalltr = char.find_all("tr")
        for tt1 in findalltr:
            th = tt1.find("th")
            td = tt1.find("td")
            makedict[th.text.strip()] = td.text.strip()

    findalltable = makesoup.find_all("table",{"class":"specifications-table"})
    for ll in findalltable:
        findalltr = ll.find_all("tr")
        for tt1 in findalltr:
            th = tt1.find("th")
            td = tt1.find("td")
            makedict[th.text.strip()] = td.text.strip()


    alltype = []
    alldocument = []
    findalla = []

    req = requests.get(f"https://www.se.com/{c1}/{c2}/product/async/productDocuments.jsp?productId={sku}&paramRangeId=&filterForTab=documents&heading=Documentos&blockId=pdp-documents")
    req.encoding = "utf-8"

    makesoup = BeautifulSoup(req.text,"lxml")
    findalla += makesoup.find_all("a")

    req = requests.get(f"https://www.se.com/{c1}/{c2}/product/async/productDocuments.jsp?productId={sku}&paramRangeId=&filterForTab=software&heading=Software%20y%20firmware&blockId=pdp-software")
    req.encoding = "utf-8"

    makesoup = BeautifulSoup(req.text,"lxml")
    findalla += makesoup.find_all("a")
    for tt3 in findalla:
        if "#" not in tt3.get("href"):
            if tt3.get("href") not in alldocument:
                alldocument.append(tt3.get("href"))
                alltype.append({"type":tt3.get("data-doc-type"), "link":tt3.get("href")})

    for tt5 in alltype:
        try:
            makedict[tt5["type"]] = makedict[tt5["type"]] + "," + tt5["link"]
        except:
            makedict[tt5["type"]] = tt5["link"]
    makedict["html"] = html_info.get(sku,"")

    return makedict

def scraping(url):
    req = requests.get(url)
    req.encoding = "utf-8"

    getdata = parse(req.text, url)
    alldata.append(getdata)
driver.quit()
with ThreadPool(30) as pool:
    results = list(tqdm(pool.imap_unordered(scraping, urls), total=len(urls)))

df = pd.DataFrame(alldata)
df.to_csv("data1.csv", index=False, encoding="utf-8-sig")