import os
import time
from random import randint

from dotenv import load_dotenv
from logger import logger as l
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from amazoncaptcha import AmazonCaptcha

load_dotenv(verbose=True)
dotenv_path = '.env'
load_dotenv(dotenv_path)

LOGIN_MAIL = os.environ.get('LOGIN_MAIL', "")
LOGIN_PASSWORD = os.environ.get('LOGIN_PASSWORD', "")

ITEM_URL = os.environ.get('ITEM_URL', "https://www.amazon.it/Sony-PlayStation-5/dp/B08KKJ37F7")

CHECKOUT_URL = "https://www.amazon.it/gp/cart/view.html?ref_=nav_cart"
ACCEPT_SHOP = "amazon"
LIMIT_VALUE = 500.  # Maximum USD for the purchase


def login(chromeDriver):
    chromeDriver.find_element_by_id("nav-link-accountList").click()
    chromeDriver.find_element_by_id('ap_email').send_keys(LOGIN_MAIL)
    chromeDriver.find_element_by_id('continue').click()
    chromeDriver.find_element_by_id('ap_password').send_keys(LOGIN_PASSWORD)
    chromeDriver.find_element_by_id('signInSubmit').click()
    l.info("Successfully logged in")


def validate_captcha(chromeDriver):
    time.sleep(1)
    l.info("Solving CAPTCHA")
    chromeDriver.get('https://www.amazon.com/errors/validateCaptcha')
    captcha = AmazonCaptcha.fromdriver(chromeDriver)
    solution = captcha.solve()
    chromeDriver.find_element_by_id('captchacharacters').send_keys(solution)
    chromeDriver.find_element_by_class_name('a-button-text').click()
    time.sleep(1)


def purchase_item(chromeDriver):
    l.info("Starting purchase process...")
    # Checks if out of stock, price is right, and shipper is amazon keeps waiting if not in stock (for a random amount of time as to not get banned)
    while not in_stock_check(chromeDriver) or not verify_price_within_limit(chromeDriver) or not seller_check(
            chromeDriver):
        l.info("Could not purchase desired item...waiting for stock/pricing/seller")
        time.sleep(randint(15, 90))
        chromeDriver.refresh()

    # Logs in and purchases the item
    login(chromeDriver)

    # Solve Captcha
    validate_captcha(chromeDriver)

    if not checkout(chromeDriver):
        return False
    return True


def in_stock_check(chromeDriver):
    l.info("Checking stock...")
    inStock = False

    try:
        if chromeDriver.find_element_by_id("priceblock_ourprice").text:
            l.info("Item is in-stock!")
            inStock = True
        elif chromeDriver.find_element_by_id("priceblock_dealprice").text:
            l.info("Item is in-stock and with a discount! BUY IT")
            inStock = True
        else:
            try:
                chromeDriver.find_element_by_id("outOfStock")
                l.info("Item is outOfStock")
                chromeDriver.refresh()
                inStock = False
            except:
                l.warn("Item is out of stock!")
    except Exception as e:
        l.error('Error checking stock: {}'.format(e))

    finally:
        return inStock


def seller_check(chromeDriver):
    l.info("Checking shipper...")
    element = chromeDriver.find_element_by_id("merchant-info").text
    shop = element.lower().find("venduto e spedito da amazon.")
    if shop == -1:
        l.warn(f"Amazon is not the seller/shipper it is: {element.lower()}")
        return False
    else:
        l.info(f"Successfully verified shipper as: {element}")
        return True


def verify_price_within_limit(chromeDriver):
    try:
        price = chromeDriver.find_element_by_id('priceblock_ourprice').text
    except Exception as e:
        l.error('Error verifying price: {}'.format(e))
        return False

    l.info(f'price of item is:  {price}')
    l.info('limit value is: {}'.format(float(LIMIT_VALUE)))

    if float(price.replace('€', '').replace(" ","").replace(",",".")) > LIMIT_VALUE:
        l.warn('PRICE IS TOO LARGE.')
        return False

    return True


def checkout(chromeDriver):
    l.info("Checking out...")
    chromeDriver.get(ITEM_URL)

    chromeDriver.find_element_by_id('submit.add-to-cart').click()  # add to cart

    chromeDriver.get(CHECKOUT_URL)

    try:
        WebDriverWait(chromeDriver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@name='proceedToRetailCheckout']"))).click()
    except Exception as e:
        l.warn(f"Could not place order: {e}")

    count = 0
    while (count < 3):
        try:
            WebDriverWait(chromeDriver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@name='placeYourOrder1']"))).click()
            l.info("Placed order!")
            return True
        except Exception as e:
            count += 1
            l.warn(f"Try: {count}, Could not place order: {e}")
    return False


def checkout_1click(chromeDriver):
    l.info("Buy now with 1-click")
    chromeDriver.find_element_by_id('buy-now-button').click()
    l.info("Confirming order")
    chromeDriver.find_element_by_name('placeYourOrder1').click()
