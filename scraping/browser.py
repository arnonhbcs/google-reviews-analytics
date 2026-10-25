import json
import logging
import time
from contextlib import contextmanager, suppress
from pathlib import Path
from urllib.parse import parse_qs

import numpy as np
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

SCREENSHOTS = Path(__file__).parent.parent / "screenshots"

TAB = (
    '//button[@role="tab" and contains(@aria-label, "Avaliações")]',
    '//button[@role="tab" and contains(@aria-label, "Reviews")]',
)
TOTAL = (
    '//span[@role="img" and contains(@aria-label, "avaliações")]',
    '//*[contains(text(), " avaliações") and not(*)]',
    '//span[@role="img" and contains(@aria-label, "reviews")]',
)
SORT = ('//button[@data-value="Ordenar"]', '//button[@data-value="Sort"]')
NEWEST = (
    '//div[@role="menuitemradio" and contains(., "Mais recentes")]',
    '//div[@role="menuitemradio" and contains(., "Newest")]',
)
LOGIN = ('//*[contains(text(), "Faça login para aproveitar")]',)
NEWEST_ORDER = 'null,[2]]",null,"generic"]]]'
FEED = (
    "/html/body/div[1]/div[2]/div[9]/div[10]/div/div/div[1]/div[4]/div/div[1]/div/div/div[2]",
)

ARGS = (
    "--window-size=1920,1080",
    "--disable-blink-features=AutomationControlled",
    "--lang=pt-BR",
)
HIDE = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
BLOCKED = ["*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif", "*googleusercontent.com/*"]
SCROLL = """
const feeds = [...document.querySelectorAll('div')].filter(el => {
    const style = getComputedStyle(el).overflowY;
    return ['auto', 'scroll'].includes(style) && el.scrollHeight > el.clientHeight;
});
const feed = feeds.sort((a, b) => b.scrollHeight - a.scrollHeight)[0];
if (feed) feed.scrollTop = feed.scrollHeight;
"""


def create_driver(profile):
    options = webdriver.ChromeOptions()
    for arg in ARGS + (f"--user-data-dir={profile}",):
        options.add_argument(arg)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument", {"source": HIDE}
    )
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": BLOCKED})
    return driver


@contextmanager
def session(profile):
    driver = create_driver(profile)
    try:
        yield driver
    except Exception:
        SCREENSHOTS.mkdir(exist_ok=True)
        driver.save_screenshot(str(SCREENSHOTS / f"{int(time.time())}.png"))
        raise
    finally:
        driver.quit()


def pause(mean=2.0, std=0.5):
    time.sleep(max(0.0, np.random.normal(mean, std)))


def find(driver, xpaths, timeout=15):
    pause(0.8, 0.2)
    conditions = (EC.element_to_be_clickable((By.XPATH, x)) for x in xpaths)
    return WebDriverWait(driver, timeout).until(EC.any_of(*conditions))


def events(driver):
    return [json.loads(e["message"])["message"] for e in driver.get_log("performance")]


def click(driver, xpaths, timeout=15, attempts=3):
    for attempt in range(attempts):
        try:
            element = find(driver, xpaths, timeout)
            text = element.text
            element.click()
            return text
        except StaleElementReferenceException:
            if attempt == attempts - 1:
                raise


def open_reviews(driver, url):
    driver.get(url)
    with suppress(TimeoutException):
        click(driver, TAB, timeout=5)


def sort_newest(driver):
    click(driver, SORT)
    events(driver)
    if "login" in click(driver, NEWEST + LOGIN).lower():
        raise PermissionError("Google Maps requires login to sort reviews")


def is_newest(request):
    freq = parse_qs(request.get("postData") or "").get("f.req", [""])[0]
    return freq.endswith(NEWEST_ORDER)


def total_reviews(driver):
    for xpath in TOTAL:
        for element in driver.find_elements(By.XPATH, xpath):
            with suppress(StaleElementReferenceException):
                text = element.get_attribute("aria-label") or element.text
                digits = "".join(c for c in text.split(" ")[0] if c.isdigit())
                if digits:
                    return int(digits)
    return None


def scroll(driver):
    feeds = [e for xpath in FEED for e in driver.find_elements(By.XPATH, xpath)]
    if feeds:
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feeds[0])
    else:
        driver.execute_script(SCROLL)


def responses(driver, rpcid="qv9Egd", idle_seconds=60):
    pending, last = {}, time.monotonic()
    while time.monotonic() - last < idle_seconds:
        scroll(driver)
        pause()
        for event in events(driver):
            params = event["params"]
            if event["method"] == "Network.requestWillBeSent":
                request = params["request"]
                if f"rpcids={rpcid}" in request["url"] and is_newest(request):
                    pending[params["requestId"]] = False
            elif event["method"] == "Network.loadingFinished":
                if params["requestId"] in pending:
                    pending[params["requestId"]] = True
        finished = [request_id for request_id, done in pending.items() if done]
        if finished:
            last = time.monotonic()
        for request_id in finished:
            del pending[request_id]
            body = driver.execute_cdp_cmd(
                "Network.getResponseBody", {"requestId": request_id}
            )
            yield body["body"]
    logging.warning("no %s response for %d s, stopping", rpcid, idle_seconds)
