import re, time, random, sys
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyquery import PyQuery as pq
import pymongo

#配置
MONGO_URL = 'localhost'
MONGO_DB = 'taobao'
MONGO_TABLE = 'product'

SERVICE_ARGS =['--disk-cache=true', '--load-images=false']
KEYWORDS = '海底捞'

if len(sys.argv) == 2:
    KEYWORDS = str(sys.argv[1])

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]

browser = webdriver.PhantomJS(service_args=SERVICE_ARGS)

browser.set_window_size(1400, 900)

wait = WebDriverWait(browser, 10)

def search():
    print('【正在搜索%s……】' % KEYWORDS)
    try:
        browser.get('https://www.taobao.com/')
        input_box = wait.until(EC.presence_of_element_located((By.ID, 'q')))
        input_box.send_keys(KEYWORDS)
        button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, '#J_TSearchForm > div.search-button > button')))
        button.click()
        total = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total')))

        get_product()
        return total.text
    except TimeoutException:
        return search()

def next_page(page_number):
    print('【正在翻页……】')
    try:
        input_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > input')))

        button  = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit')))

        input_box.clear()
        input_box.send_keys(page_number)

        button.click()

        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active > span'), str(page_number)))

        get_product()
    except TimeoutException:
        next_page(page_number)


def get_product():
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-itemlist > div')))
    lis = browser.find_elements(By.CSS_SELECTOR, '#mainsrp-itemlist .items .item')
    for item in lis:
        product = {
            'title': item.find_element(By.CSS_SELECTOR, '.title').text,
            'price': item.find_element(By.CSS_SELECTOR, '.price').text,
            'deal': item.find_element(By.CSS_SELECTOR, '.deal-cnt').text,
            'shop': item.find_element(By.CSS_SELECTOR, '.shop').text,
            'location': item.find_element(By.CSS_SELECTOR, '.location').text
        }
        link = item.find_element(By.CSS_SELECTOR, '.title a')
        link.click()
        browser.switch_to_window(browser.window_handles[1])
        print('>>>>>> 标题：' + browser.title)

        time.sleep(random.randint(3, 6))
        html = pq(browser.page_source)

        if browser.title.endswith('天猫'):
            product['m_sell'] = html.find('#detail .tm-ind-panel .tm-ind-sellCount .tm-count').text()
            product['t_comt'] = html.find('#detail .tm-ind-panel .tm-ind-reviewCount .tm-count').text()
        else:
            product['m_sell'] = html.find('#detail .tb-meta .tb-counter .tb-sell-counter strong').text()
            product['t_comt'] = html.find('#detail .tb-meta .tb-counter .tb-rate-counter strong').text()
        
        browser.close()
        browser.switch_to_window(browser.window_handles[0])
        
        save_to_mongo(product)

def save_to_mongo(result):
    try:
        if db[MONGO_TABLE].insert(result):
            print('【保存到Mongodb成功】', result)

    except Exception:
        print('【保存到Mongodb失败】', result)

def main():

    try:
        total = search()
        total = int(re.compile(r'(\d+)').search(total).group(1))
        for page_number in range(2,total + 1):
            next_page(page_number)

    except Exception:
        print('【出错了】')

    finally:
        browser.quit()

if __name__=='__main__':
    main()