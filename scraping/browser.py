import json
import logging
import time
from contextlib import contextmanager, suppress
from pathlib import Path

import numpy as np
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

SCREENSHOTS = Path(__file__).parent.parent / "screenshots"

TAB = (
    '//button[@role="tab" and contains(@aria-label, "Avaliações")]',
    '//button[@role="tab" and contains(@aria-label, "Reviews")]',
)
FEED = (
    "/html/body/div[1]/div[2]/div[9]/div[10]/div/div/div[1]/div[4]/div/div[1]/div/div/div[2]",
)

ARGS = (
    "--window-size=1920,1080",
    "--disable-blink-features=AutomationControlled",
    "--lang=pt-BR",
)
HIDE = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
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
    pause()
    conditions = (EC.element_to_be_clickable((By.XPATH, x)) for x in xpaths)
    return WebDriverWait(driver, timeout).until(EC.any_of(*conditions))


def events(driver):
    return [json.loads(e["message"])["message"] for e in driver.get_log("performance")]


def open_reviews(driver, url):
    driver.get(url)
    with suppress(TimeoutException):
        find(driver, TAB, timeout=5).click()
    events(driver)


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
                if f"rpcids={rpcid}" in params["request"]["url"]:
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
