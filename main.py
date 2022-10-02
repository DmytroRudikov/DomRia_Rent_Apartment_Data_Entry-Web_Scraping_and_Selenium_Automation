from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
import requests
import time
import csv
import pandas as pd
import os

## Some basic configurations at the beginning
# < ----- Site to use for the flats search and data scraping ----- >
dom_source = "https://dom.ria.com/uk/arenda-kvartir/kiev-1k/"
# < ----- Path to google-form to complete ----- >
google_form = os.getenv("GOOGLE_FORM")

## Project start
# < ----- Parse Dom.Ria site to find 1-room apartments for rent in Kyiv ----- >
response = requests.get(dom_source).text
# with open("domria_for_testing.html", encoding="utf-8") as file:
#     domria_parsed = file.read()
soup = BeautifulSoup(response, "html.parser")

# # < ----- Create a list of suggested flats on the first page of the site ----- >
property_list = soup.select("div#domSearchPanel section.realty-item.isStringView")

# < ----- Loop through each property and extract needed information from the scraped website
#         Create lists to fill in search results scraped from the website ----- >
prices = [prop.select_one("b.size18").string.strip().strip(" грн").split()[0] +
          prop.select_one("b.size18").string.strip().strip(" грн").split()[1] for prop in property_list]
sq_m = [prop.select("div.mt-10.chars.grey span")[1].getText().strip().strip(" м²") for prop in property_list]
addresses = [prop.select_one("h2.tit a").getText().strip() for prop in property_list]
districts = []
subway_stations = []
hrefs_for_master = []
hrefs = []

for prop in property_list:
    if prop.select_one("a.mb-5.i-block.grey.p-rel").getText().strip().strip(", ") == "":
        districts.append("N/A")
    else:
        districts.append(prop.select_one("a.mb-5.i-block.grey.p-rel").getText().strip().strip(", "))

for prop in property_list:
    if prop.find(name="a", attrs={"data-level": "metro"}) is None:
        subway_stations.append("N/A")
    else:
        subway_stations.append(prop.find(name="a", attrs={"data-level": "metro"}).getText().strip())

for prop in property_list:
    if "https://dom.ria.com" not in prop.select_one("h2.tit a").get("href"):
        link = "https://dom.ria.com" + prop.select_one("h2.tit a").get("href")
    else:
        link = prop.select_one("h2.tit a").get("href")
    hrefs.append(link)
    hrefs_for_master.append(link)

master_list = [prices, sq_m, addresses, districts, subway_stations, hrefs_for_master]

# < ----- Verify whether there is no duplicate postings being made to the DTB
#         and post only unique entries of flats found on the site ----- >
try:
    data = "1-room_domria_flats_kyiv.csv"
    flats_df = pd.read_csv(data)
    for link_entry in hrefs:
        if link_entry in flats_df.Link.values:
            duplicate_ind = master_list[-1].index(link_entry)
            for item in master_list:
                item.pop(duplicate_ind)
except FileNotFoundError:
    file = open("1-room_domria_flats_kyiv.csv", mode="a", newline="", encoding="utf-8")
    field_names = ["Flat's Price, UAH", "Square Meters (m²)", "Address", "Kyiv District",
                   "Metro Station Nearby", "Link"]
    writer_dict_obj = csv.DictWriter(file, fieldnames=field_names)
    writer_dict_obj.writeheader()
else:
    file = open("1-room_domria_flats_kyiv.csv", mode="a", newline="", encoding="utf-8")
    field_names = ["Flat's Price, UAH", "Square Meters (m²)", "Address", "Kyiv District",
                   "Metro Station Nearby", "Link"]
    writer_dict_obj = csv.DictWriter(file, fieldnames=field_names)
finally:
    for n in range(len(master_list[-1])):
        row_to_write = {field_names[field]: master_list[field][n] for field in range(len(field_names))}
        writer_dict_obj.writerow(row_to_write)
    file.close()

## Selenium google form data entry automation
if len(master_list[0]) == 0:
    print("No new flats found")
else:
    # < ----- Activate Selenium ----- >
    SELENIUM_DRIVER_PATH = os.environ.get("SELENIUM_DRIVER_PATH")
    service = ChromeService(executable_path=SELENIUM_DRIVER_PATH)
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # < ----- Open a form to fill ----- >
    driver.get(google_form)
    time.sleep(2)

    # < ----- Fill in the form with Selenium ----- >
    for i in range(len(prices)):
        div = driver.find_element(by=By.CLASS_NAME, value="o3Dpx")
        form_inputs = div.find_elements(By.TAG_NAME, "input")
        for n in range(len(master_list)):
            form_inputs[n].send_keys(master_list[n][i])
        driver.find_element(By.XPATH, '//*[@id="mG61Hd"]/div[2]/div/div[3]/div[1]/div[1]/div/span/span').click()
        time.sleep(1)
        if i == len(prices) - 1:
            pass
        else:
            driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[1]/div/div[4]/a").click()
            time.sleep(1)

    # < ----- Close Selenium ----- >
    driver.quit()
