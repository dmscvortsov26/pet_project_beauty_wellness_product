from playwright.async_api import (async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError)

import json
from json import JSONDecodeError

import asyncio

from abc import ABC, abstractmethod

import time
import os
import subprocess 

import urllib.request
from pathlib import Path
import uuid
from urllib.parse import quote, urlsplit

from tqdm import tqdm

from psycopg.rows import dict_row
import psycopg

import pandas as pd 
import matplotlib.pyplot as plt

import copy

"""
НАСТРОЙКИ БРАУЗЕРА
"""
CDP_URL = "http://127.0.0.1:9222"
PROFILE_DIR = (Path(os.environ["LOCALAPPDATA"])/"GoldApplePet"/"YandexCDP")

YANDEX_PATH = None

def find_yandex():
    if YANDEX_PATH:
        path = Path(YANDEX_PATH)

        if not path.is_file():
            raise FileNotFoundError(f"Браузер не найдет {path}")

        return path

    for variable in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)",):
        directory = os.environ.get(variable)

        if not directory:
            continue

        path = (
            Path(directory)/"Yandex"/"YandexBrowser"/"Application"/"browser.exe"
        )

        if path.is_file():
            return path
        
    raise FileNotFoundError(f"Yandex не найден. Укажи путь в YANDEX_PATH")


def cdp_is_available():
    opener = urllib.request.build_opener( # создали HTTP-клиент
        urllib.request.ProxyHandler({}) # отключили proxy
        )

    try:
        with opener.open(f"{CDP_URL}/json/version", timeout=1) as response: # сделали GET-запрос к локальному CDP
            data = json.load(response)

        return bool(
            data.get("webSocketDebuggerUrl") # превратили JSON-ответ в Python dict, если есть True
        )
    except (ValueError, OSError):
        return False


def local_http(path, method="GET", parse_json=True):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({})
    )

    request = urllib.request.Request(
        CDP_URL + path,
        method=method
    )

    with opener.open(request, timeout=5) as response:
        text = response.read().decode("utf-8")

    return json.loads(text) if parse_json else text


async def create_tab(url):
    target = await asyncio.to_thread(
        local_http,
        "/json/new?" + quote(url, safe=""),
        "PUT",
    )

    if not isinstance(target, dict) or not target.get("id"):
        raise RuntimeError("Браузер не вернул ID новой вкладки.")

    return target


async def start_yandex():
    if await asyncio.to_thread(cdp_is_available):
        print(
            "На порту 9222 уже работает браузер.\n"
            "Продолжаем работать с существующим Yandex"
        )
        return
    
    PROFILE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    subprocess.Popen( # Запускает Яндекс
    [
        str(find_yandex()), # путь до Яндекса
        "--remote-debugging-address=127.0.0.1", # CDP доступен локально на твоём компьютере.
        "--remote-debugging-port=9222", # браузер слушает порт 9222.
        f"--user-data-dir={PROFILE_DIR}", # использовать наш постоянный профиль
        "https://goldapple.ru/parfjumerija", # сразу открыть GoldApple.
    ],
    stdout=subprocess.DEVNULL, # nе выводить технический stdout/stderr процесса Yandex в наш Python-терминал.
    stderr=subprocess.DEVNULL,
)
    for _ in range(30):
        if await asyncio.to_thread(cdp_is_available):
            print("Yandex запущен. CDP доступен.")
            return 

        await asyncio.sleep(0.5)

    raise RuntimeError( 
                    "CDP не запустился. Проверь выделенное окно "
                    "Yandex и порт 9222.")


class AsyncBrowserSession:

    async def __aenter__(self):

        self.markers = [
            f"about:blank#ga-pool-{uuid.uuid4().hex}"
            for _ in range(5)
        ]
        for marker in self.markers:
            await create_tab(marker)

        for _ in range(30):

            targets = await asyncio.to_thread(
                local_http,
                "/json/list"
            )
            existing_urls = {
                target.get("url")
                for target in targets
            }

            if set(self.markers) <= existing_urls:
                break

            await asyncio.sleep(0.2)

        else:
            raise RuntimeError(
                "Созданные вкладки не появились в CDP."
            )

        self.p = await async_playwright().start()

        try:
            self.browser = await self.p.chromium.connect_over_cdp(
                CDP_URL,
                timeout=15_000
            )

            if not self.browser.contexts:
                raise RuntimeError(
                    "В подключённом браузере нет контекста."
                )

            self.context = self.browser.contexts[0]

            pages_by_url = {
                page.url: page
                for page in self.context.pages
            }

            if not all(
                marker in pages_by_url
                for marker in self.markers
            ):
                raise RuntimeError(
                    "Playwright не увидел все созданные вкладки."
                )

            self.pool = asyncio.Queue()

            for marker in self.markers:
                self.pool.put_nowait(
                    pages_by_url[marker]
                )

            return self.context, self.pool

        except BaseException:
            await self.p.stop()
            raise


    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback
    ):
        await self.p.stop()


class CatalogCollector:

    def __init__(self, page, catalog_url, category):
        self.page = page  # -> текущий Playwright Page  
        self.catalog_url = catalog_url # -> url категории (Парфюмерия, БАДы и уходовая косметика)
        self.category = category # -> категория 

    async def collect_products(self):

        def is_cards_list(response):
            parsed = urlsplit(response.url)
            return (
                    parsed.hostname == "goldapple.ru"
                    and parsed.path == "/front/api/catalog/cards-list"
                    and response.request.method == "POST"
                    )

        async with self.page.expect_response(is_cards_list,timeout=10_000) as response_info:

            await self.page.goto(self.catalog_url,timeout=10_000)
        cards_response = await response_info.value
        print(
                f"[CATALOG INITIAL] "
                f"method={cards_response.request.method} "
                f"status={cards_response.status} "
                f"url={cards_response.url}",
                flush=True,
            )           

        content_type = cards_response.headers.get("content-type","")

        if cards_response.status == 403:
            raise RuntimeError(
                "GoldApple source blocked: HTTP 403"
            )

        if "application/json" not in content_type:
            raise RuntimeError(
                f"Expected JSON, got {content_type}"
            )
        data = await cards_response.json()

        request = cards_response.request
        payload = json.loads(request.post_data)

        new_payload = payload.copy()

        
        while True:
            product_list = []

            cards = data["data"]["cards"]
            for card in cards:
                if "product" not in card:
                    continue
                one_product = card["product"]

                product_list.append(
                        {
                        "url": "https://goldapple.ru"+one_product["url"],
                        "price_actual": one_product["price"]["actual"]["amount"],
                        "category": self.category
                        }
                    )

            yield product_list

            if not data["data"]["pagination"]["nextPage"]:
                break

            if new_payload["pageNumber"] == 20:
                break
            new_payload["pageNumber"] += 1

            await asyncio.sleep(1.5)

            for attempt in range(1, 4):

                try:
                    response_api = await self.page.request.post(
                        cards_response.url,
                        data=new_payload,
                        timeout=10_000
                    )

                    break

                except PlaywrightError as error:

                    if "socket hang up" not in str(error).lower():
                        raise

                    print(
                        f"[CATALOG] CONNECTION ERROR | "
                        f"pageNumber={new_payload['pageNumber']} | "
                        f"attempt={attempt}",
                        flush=True
                    )

                    if attempt == 3:
                        raise

                    await asyncio.sleep(5 * attempt)

            print(
                    f"[CATALOG PAGINATION] "
                    f"pageNumber={new_payload['pageNumber']} "
                    f"status={response_api.status}",
                    flush=True,
                )

            content_type = response_api.headers.get("content-type","")

            if response_api.status == 403:
                raise RuntimeError(
                    "GoldApple source blocked: HTTP 403"
                )

            if "application/json" not in content_type:
                raise RuntimeError(
                    f"Expected JSON, got {content_type}"
                )
            data = await response_api.json()


        return


class Product(ABC):

    def __init__(self, page, catalog_product):
        self.page = page
        self.url = catalog_product["url"] 
        self.price_actual = catalog_product["price_actual"]
        self.category = catalog_product["category"]

    @abstractmethod
    async def collect_data(self):
        pass


class PerfumeProduct(Product):

    async def collect_data(self):

        def is_product_card(response):
            return "product-card/base" in response.url
        
        def is_rating_card(response): 
            return "layout-type" in response.url
        async with (
            self.page.expect_response(is_product_card, timeout=10_000) as product_response_info,
            self.page.expect_response(is_rating_card, timeout=10_000) as rating_response_info
        ):
            await self.page.goto(self.url, timeout=10_000)

        product_response = await product_response_info.value
        product_data = await product_response.json()

        rating_response = await rating_response_info.value
        rating_data = await rating_response.json()

        descriptions1 = product_data["data"]
        product_info1 = {
                'itemId': descriptions1["itemId"],
                'mainVariantItemId': descriptions1["mainVariantItemId"],
                'name': descriptions1["name"],
                'brand': descriptions1["brand"],
                'productType': descriptions1["productType"],
                'url': self.url,
                'price_actual': self.price_actual,
                'category': self.category
                }

        descriptions2 = product_data["data"]["productDescription"]
        attributes = []

        for line in descriptions2:
            if "attributes" in line:
                attributes = line["attributes"]
                break

        product_info2 = {}

        for el in attributes:
            product_info2[el["key"]] = el["value"]


        descriptions = rating_data["data"]["widgets"]["fullhd"]

        product_info3 = {
            "rating": descriptions[0]["data"]["rating"], # рейтинг (оценка)
            "recommended": descriptions[0]["data"]["recommended"], # процент рекомендаций
            "review_count": descriptions[0]["data"]["allReviewsCount"], # кол-во отзывов
            "star_statistic": descriptions[0]["data"]["starStatistic"] # детализация (оценка звёзд) 
        }

        result_data = {
                'item_id': product_info1["itemId"],
                'main_variant_item_id': product_info1["mainVariantItemId"],
                'name': product_info1["name"],
                'brand': product_info1["brand"],
                'product_type': product_info1["productType"],
                'url': product_info1["url"],
                'price_actual': product_info1["price_actual"],
                'category': product_info1["category"],
                'gender': product_info2.get("для кого"),
                'product_attribute_type': product_info2.get("тип продукта"),
                'fragrance_group': product_info2.get("группа ароматов"),
                'top_notes': product_info2.get("верхние ноты"),
                'middle_notes': product_info2.get("средние ноты"),
                'base_notes': product_info2.get("базовые ноты"),
                'volume': product_info2.get("объём"),
                'rating': product_info3.get("rating"),
                'recommended': product_info3.get("recommended"),
                'review_count': product_info3.get("review_count"),
                'star_5_pct': product_info3.get("star_statistic")[0]["percent"],
                'star_4_pct': product_info3.get("star_statistic")[1]["percent"],
                'star_3_pct': product_info3.get("star_statistic")[2]["percent"],
                'star_2_pct': product_info3.get("star_statistic")[3]["percent"],
                'star_1_pct': product_info3.get("star_statistic")[4]["percent"]
                }

        return result_data

        
class SupplementProduct(Product):

    async def collect_data(self):
 
        def is_product_card(response):
            return "product-card/base" in response.url
        
        def is_rating_card(response):
            return "layout-type" in response.url
        
        async with (
            self.page.expect_response(is_product_card, timeout=10_000) as product_response_info,
            self.page.expect_response(is_rating_card, timeout=10_000) as rating_response_info            
        ):
            await self.page.goto(self.url, timeout=10_000)

        product_response = await product_response_info.value
        product_data = await product_response.json()

        rating_response = await rating_response_info.value
        rating_data = await rating_response.json()


        descriptions1 = product_data["data"]
        product_info1 = {
            'itemId': descriptions1["itemId"],
            'mainVariantItemId': descriptions1["mainVariantItemId"],
            'name': descriptions1["name"],
            'brand': descriptions1["brand"],
            'productType': descriptions1["productType"],
            'url': self.url,
            'price_actual': self.price_actual,
            'category': self.category            
        }

        descriptions2 = product_data["data"]["productDescription"]
        attributes = []

        for line in descriptions2:
            if "attributes" in line:
                attributes = line["attributes"]
                break

        product_info2 = {}

        for el in attributes:
            product_info2[el["key"]] = el["value"]


        descriptions = rating_data["data"]["widgets"]["fullhd"]

        product_info3 = {
            "rating": descriptions[0]["data"]["rating"], # рейтинг (оценка)
            "recommended": descriptions[0]["data"]["recommended"], # процент рекомендаций
            "review_count": descriptions[0]["data"]["allReviewsCount"], # кол-во отзывов
            "star_statistic": descriptions[0]["data"]["starStatistic"] # детализация (оценка звёзд) 
        }

        result_data = {
            'item_id': product_info1["itemId"],
            'main_variant_item_id': product_info1["mainVariantItemId"],
            'name': product_info1["name"],
            'brand': product_info1["brand"],
            'product_type': product_info1["productType"],
            'url': product_info1["url"],
            'price_actual': product_info1["price_actual"],
            'category': product_info1["category"],
            'gender': product_info2.get("для кого"),
            'product_attribute_type': product_info2.get("тип продукта"),
            'intended_use': product_info2.get("назначение"),
            'main_component': product_info2.get("основной компонент"),
            'release_form': product_info2.get("форма выпуска"),
            'supplement_type': product_info2.get("тип препарата"),
            'hypoallergenic': product_info2.get("гипоаллергенно"),
            'volume': product_info2.get("объём"),
            'rating': product_info3.get("rating"),
            'recommended': product_info3.get("recommended"),
            'review_count': product_info3.get("review_count"),
            'star_5_pct': product_info3.get("star_statistic")[0]["percent"],
            'star_4_pct': product_info3.get("star_statistic")[1]["percent"],
            'star_3_pct': product_info3.get("star_statistic")[2]["percent"],
            'star_2_pct': product_info3.get("star_statistic")[3]["percent"],
            'star_1_pct': product_info3.get("star_statistic")[4]["percent"]
        }

        return result_data


class SkincareProduct(Product):

    async def collect_data(self):

        def is_product_card(response):
            return "product-card/base" in response.url
        
        def is_rating_card(response):
            return "layout-type" in response.url
        
        async with (
            self.page.expect_response(is_product_card, timeout=10_000) as product_response_info,
            self.page.expect_response(is_rating_card, timeout=10_000) as rating_response_info            
        ):
            await self.page.goto(self.url, timeout=10_000)

        product_response = await product_response_info.value
        product_data = await product_response.json()

        rating_response = await rating_response_info.value
        rating_data = await rating_response.json()


        descriptions1 = product_data["data"]
        product_info1 = {
            'itemId': descriptions1["itemId"],
            'mainVariantItemId': descriptions1["mainVariantItemId"],
            'name': descriptions1["name"],
            'brand': descriptions1["brand"],
            'productType': descriptions1["productType"],
            'url': self.url,
            'price_actual': self.price_actual,
            'category': self.category               
        }

        descriptions2 = product_data["data"]["productDescription"]
        attributes = []

        for line in descriptions2:
            if "attributes" in line:
                attributes = line["attributes"]
                break

        product_info2 = {}

        for el in attributes:
            product_info2[el["key"]] = el["value"]


        descriptions = rating_data["data"]["widgets"]["fullhd"]

        product_info3 = {
            "rating": descriptions[0]["data"]["rating"], # рейтинг (оценка)
            "recommended": descriptions[0]["data"]["recommended"], # процент рекомендаций
            "review_count": descriptions[0]["data"]["allReviewsCount"], # кол-во отзывов
            "star_statistic": descriptions[0]["data"]["starStatistic"] # детализация (оценка звёзд) 
        }

        result_data = {
            'item_id': product_info1["itemId"],
            'main_variant_item_id': product_info1["mainVariantItemId"],
            'name': product_info1["name"],
            'brand': product_info1["brand"],
            'product_type': product_info1["productType"],
            'url': product_info1["url"],
            'price_actual': product_info1["price_actual"],
            'category': product_info1["category"],
            'product_attribute_type': product_info2.get("тип продукта"),
            'gender': product_info2.get("для кого"),
            'intended_use': product_info2.get("назначение"),
            'skin_type': product_info2.get("тип кожи"),
            'time_use': product_info2.get("время нанесения"),
            'area_use': product_info2.get("область применения"),
            'main_component': product_info2.get("действующий компонент"),
            'volume': product_info2.get("объём"),
            'travel_format': product_info2.get("тревел-формат"),
            'age_use': product_info2.get("возраст"),
            'flg_spf': product_info2.get("spf"),
            'rating': product_info3.get("rating"),
            'recommended': product_info3.get("recommended"),
            'review_count': product_info3.get("review_count"),
            'star_5_pct': product_info3.get("star_statistic")[0]["percent"],
            'star_4_pct': product_info3.get("star_statistic")[1]["percent"],
            'star_3_pct': product_info3.get("star_statistic")[2]["percent"],
            'star_2_pct': product_info3.get("star_statistic")[3]["percent"],
            'star_1_pct': product_info3.get("star_statistic")[4]["percent"]
        }

        return result_data
