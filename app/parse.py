import csv
from dataclasses import dataclass, fields
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from tqdm import tqdm

BASE_URL = "https://webscraper.io/"
HOME_URL = urljoin(BASE_URL, "test-sites/e-commerce/more/")
PAGES = {
    "home": HOME_URL,
    "computers": urljoin(HOME_URL, "computers"),
    "laptops": urljoin(HOME_URL, "computers/laptops"),
    "tablets": urljoin(HOME_URL, "computers/tablets"),
    "phones": urljoin(HOME_URL, "phones"),
    "touch": urljoin(HOME_URL, "phones/touch")
}


@dataclass
class Product:
    title: str
    description: str
    price: float
    rating: int
    num_of_reviews: int


PRODUCT_FIELDS = [field.name for field in fields(Product)]


class Scraper:
    def __init__(self, headless: bool = True) -> None:
        options = Options()
        options.headless = headless
        self.driver = webdriver.Chrome(options=options)
        self.cookies_accepted = False

    def accept_cookies(self) -> None:
        if self.cookies_accepted:
            return
        try:
            cookie = WebDriverWait(self.driver, 3).until(
                ec.presence_of_element_located(
                    (By.CLASS_NAME, "acceptCookies"))
            )
            if cookie:
                cookie.click()
                self.cookies_accepted = True
        except ElementClickInterceptedException:
            print("Element was not clickable. Skipping.")

    def click_load_more(self) -> None:
        try:
            button = WebDriverWait(self.driver, 1).until(
                ec.presence_of_element_located(
                    (By.CLASS_NAME, "ecomerce-items-scroll-more"))
            )

            while button and button.is_displayed():
                button.click()
                time.sleep(0.2)
        except TimeoutException:
            print("More button not found. Moving on.")

    @staticmethod
    def get_product(product_soup: BeautifulSoup) -> Product:
        return Product(
            title=product_soup.select_one(".title")["title"],
            description=(product_soup.select_one(".description").
                         text.replace("\xa0", " ").strip()),
            price=float(product_soup.select_one(".price").
                        text.replace("$", "")),
            rating=int(len(product_soup.find_all("span",
                                                 class_="ws-icon-star"))),
            num_of_reviews=int(product_soup.select_one(".review-count").
                               text.split(" ")[0])
        )

    def get_page(self, page_url: str) -> [Product]:
        self.driver.get(page_url)
        self.accept_cookies()
        self.click_load_more()
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        products = soup.select(".thumbnail")

        return [self.get_product(product) for product in products]

    @staticmethod
    def write_products_to_csv(
            output_csv_path: str,
            products: [Product]
    ) -> None:
        with open(output_csv_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(PRODUCT_FIELDS)
            for product in products:
                formatted_product = (
                    product.title,
                    product.description,
                    product.price,
                    product.rating,
                    product.num_of_reviews
                )
                writer.writerow(formatted_product)

    def close(self) -> None:
        self.driver.close()


def get_all_products() -> None:
    scraper = Scraper()
    for page_name, page_url in tqdm(PAGES.items()):
        products = scraper.get_page(page_url)
        csv_filename = f"{page_name}.csv"
        scraper.write_products_to_csv(csv_filename, products)

    scraper.close()


if __name__ == "__main__":
    get_all_products()
