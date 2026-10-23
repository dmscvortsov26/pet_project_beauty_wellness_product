import asyncio
import time

from json import JSONDecodeError
from tqdm import tqdm
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from parser.collector import (
    start_yandex,
    AsyncBrowserSession,
    CatalogCollector,
    PerfumeProduct,
    SkincareProduct,
    SupplementProduct,
)

from parser.db_loader import insert_product_to_db

""" 
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
КОД ДЛЯ ЗАПУСКА ПАРСИНГА
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
"""

categories_product = {
    "perfume": 
    {
        "url": "https://goldapple.ru/parfjumerija",
        "product_class": PerfumeProduct 
    }
    ,
    "supplements": 
    {
        "url": "https://goldapple.ru/aptechnaja-kosmetika/bady",
        "product_class": SupplementProduct
    }
    ,
    "skincare": 
    {
        "url": "https://goldapple.ru/uhod",
        "product_class": SkincareProduct
    }
}


async def main():

    await start_yandex()

    answer = await asyncio.to_thread(
        input,
        "\nДождись загрузки GoldApple в выделенном Yandex.\n"
        "Если каталог работает — нажми Enter.\n"
        "Если появился checking device — введи stop.\n> "
    )

    if answer.strip():
        print("Сбор остановлен до начала парсинга.")
        return [], []

    browser_session = AsyncBrowserSession()

    async with browser_session as (context, pool):

        all_product = []
        failed_products = []

        stats = {
            "catalog_attempts": 0,
            "product_attempts": 0,
            "retries": 0,
            "by_category": {
                category: {
                    "valid": 0,
                    "failed": 0
                }
                for category in categories_product
            }
        }

        for category, value in categories_product.items():

            catalog_list = None

            for attempt in range(1, 4):

                catalog_page = None
                stats["catalog_attempts"] += 1

                try:
                    catalog_page = await pool.get()

                    await catalog_page.goto(
                        "about:blank",
                        wait_until="commit"
                    )

                    catalog_collector = CatalogCollector(
                        catalog_page,
                        catalog_url=value["url"],
                        category=category
                    )

                    catalog_pages = catalog_collector.collect_products()
                    catalog_list = await anext(catalog_pages, None)

                    break

                except (
                    TimeoutError,
                    JSONDecodeError,
                    PlaywrightTimeoutError
                ) as error:

                    print(
                        f"[CATALOG] ERROR {attempt} | "
                        f"{type(error).__name__}: {error}"
                    )

                finally:
                    if catalog_page is not None:
                        pool.put_nowait(catalog_page)

                if attempt < 3:
                    await asyncio.sleep(1 * attempt)

            if catalog_list is None:
                continue

            try:
                while catalog_list is not None:

                    pbar = tqdm(
                        total=len(catalog_list),
                        desc=category,
                        unit="product",
                        dynamic_ncols=True
                    )

                    async def collect_one_product(
                        pool,
                        type_class,
                        catalog_product,
                        semaphore,
                        start_lock,
                        pbar
                    ):

                        try:

                            async with semaphore:

                                for attempt in range(1, 4):

                                    page = None

                                    stats["product_attempts"] += 1

                                    try:
                                        page = await pool.get()

                                        await page.goto(
                                            "about:blank",
                                            wait_until="commit"
                                        )

                                        product = type_class(
                                            page,
                                            catalog_product
                                        )

                                        async with start_lock:
                                            await asyncio.sleep(0.7)

                                        result = await asyncio.wait_for(
                                            product.collect_data(),
                                            timeout=15
                                        )

                                        stats["by_category"][
                                            catalog_product["category"]
                                        ]["valid"] += 1

                                        return result

                                    except (
                                        TimeoutError,
                                        JSONDecodeError,
                                        PlaywrightTimeoutError
                                    ) as error:

                                        if attempt == 3:

                                            stats["by_category"][
                                                catalog_product["category"]
                                            ]["failed"] += 1

                                            failed_products.append(
                                                {
                                                    "url": catalog_product["url"],
                                                    "category": catalog_product["category"],
                                                    "error_type": type(error).__name__,
                                                    "error_message": str(error),
                                                    "attempts": attempt
                                                }
                                            )

                                    except (
                                        KeyError,
                                        TypeError,
                                        AttributeError
                                    ) as error:

                                        stats["by_category"][
                                            catalog_product["category"]
                                        ]["failed"] += 1

                                        failed_products.append(
                                            {
                                                "url": catalog_product["url"],
                                                "category": catalog_product["category"],
                                                "error_type": type(error).__name__,
                                                "error_message": str(error),
                                                "attempts": attempt
                                            }
                                        )

                                        return None

                                    finally:

                                        if page is not None:
                                            pool.put_nowait(page)

                                    if attempt < 3:
                                        stats["retries"] += 1
                                        await asyncio.sleep(1 * attempt)

                        finally:
                            pbar.update(1)

                    coroutines = []

                    semaphore = asyncio.Semaphore(5)
                    start_lock = asyncio.Lock()

                    for catalog_product in catalog_list:

                        type_class = value["product_class"]

                        coroutines.append(
                            collect_one_product(
                                pool,
                                type_class,
                                catalog_product,
                                semaphore,
                                start_lock,
                                pbar
                            )
                        )

                    tasks = [
                        asyncio.create_task(coroutine)
                        for coroutine in coroutines
                    ]

                    try:
                        result_product = await asyncio.gather(*tasks)

                    except BaseException:
                        for task in tasks:
                            task.cancel()

                        await asyncio.gather(
                            *tasks,
                            return_exceptions=True
                        )
                        raise

                    finally:
                        pbar.close()

                    valid_results = [
                        result
                        for result in result_product
                        if result is not None
                    ]

                    all_product.extend(valid_results)

                    await asyncio.sleep(0.5)

                    catalog_page = None

                    try:
                        catalog_page = await pool.get()
                        catalog_collector.page = catalog_page

                        catalog_list = await anext(catalog_pages, None)

                        if catalog_list is not None:
                            stats["catalog_attempts"] += 1

                    finally:
                        if catalog_page is not None:
                            pool.put_nowait(catalog_page)

            finally:
                await catalog_pages.aclose()

        for category, category_stats in stats["by_category"].items():

            print(
                f"{category}: "
                f"valid={category_stats['valid']} | "
                f"failed={category_stats['failed']}"
            )

        print(f"Valid products: {len(all_product)}")
        print(f"Failed products: {len(failed_products)}")
        print(f"Catalog attempts: {stats['catalog_attempts']}")
        print(f"Product attempts: {stats['product_attempts']}")
        print(f"Retries: {stats['retries']}")

        return all_product, failed_products


if __name__ == "__main__":
    start_time = time.perf_counter()

    all_product, failed_products = asyncio.run(main())

    if all_product:
        insert_product_to_db(all_product)
    else:
        print("Нет товаров для загрузки.")

    elapsed_time = time.perf_counter() - start_time
    print(f"Время выполнения: {elapsed_time:.4f} сек.")