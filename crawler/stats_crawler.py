from selenium import webdriver
from urllib.parse import urlparse, parse_qs
from retrying import retry
import csv
import time
import re
import requests
import json

champion_names = []

response = requests.get(
    "https://cdn.lolalytics.com/v/current/tooltip/eng/champion.json")
data = json.loads(response.text)

for key, value in data.items():
    champion_name = value.split("<h3>")[1].split("</h3>")[0]
    champion_names.append(
        champion_name.lower().replace(' ', '').replace('\'', '').replace('.', ''))

lanes = ['top', 'jungle', 'middle', 'bottom', 'support']


@retry
def get_driver(champion_name, lane):
    url = "https://lolalytics.com/lol/" + champion_name + \
        "/build/?lane=" + lane + "&tier=all"
    driver = webdriver.Firefox()
    driver.get(url)
    return driver


@retry
def get_counters_from_driver(driver):
    CountersPanel_counters__U8zc5 = driver.find_elements_by_class_name(
        "CountersPanel_counters__U8zc5")
    return CountersPanel_counters__U8zc5


for lane in lanes:
    for champion_name in champion_names:
        driver = get_driver(champion_name, lane)
        counters = get_counters_from_driver(driver)

        driver.execute_script(
            "arguments[0].scrollIntoView();", counters[0])

        class Data:
            def __init__(self, champion, vslane, win_rate, games):
                self.champion = champion
                self.vslane = vslane
                self.win_rate = win_rate
                self.games = games

            def __eq__(self, other):
                return self.champion == other.champion and self.vslane == other.vslane

            def __hash__(self):
                return hash((self.champion, self.vslane))

        datas = []

        for i in range(1, len(counters) + 1):
            counter = counters[i - 1]
            Panel_data__dtE8F = counter.find_element_by_class_name(
                "Panel_data__dtE8F")
            for j in range(0, 16):
                driver.execute_script(
                    "document.getElementsByClassName(\"Panel_data__dtE8F\")[" + str(i) + "].scroll(" + str(j * 890) + ", 0)")

                Cell_cell__383UV = counter.find_elements_by_class_name(
                    "Cell_cell__383UV")
                for cell in Cell_cell__383UV:
                    a = cell.find_element_by_tag_name("a")
                    href = a.get_attribute("href")
                    parsed_url = urlparse(href)
                    query = parse_qs(parsed_url.query)

                    match = re.search(r'/vs/(.*?)/', parsed_url.path)

                    champion = match.group(1)
                    vslane = query.get("vslane", [None])[0]

                    numbers = [float(n) if ',' not in n else float(
                        n.replace(',', '')) for n in cell.text.split('\n')]

                    win_rate = numbers[0]
                    games = int(numbers[-1])

                    data = Data(champion, vslane, win_rate, games)
                    datas.append(data)

        driver.quit()

        unique_datas = list(set(datas))
        sorted_datas = sorted(
            unique_datas, key=lambda x: x.games, reverse=True)
        with open(champion_name + "_" + lane + ".csv", "w") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["champion", "vslane", "win_rate", "games"])
            for data in sorted_datas:
                writer.writerow([data.champion, data.vslane,
                                data.win_rate, data.games])
