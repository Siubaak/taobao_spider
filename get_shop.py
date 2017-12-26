import re, time, random, sys
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyquery import PyQuery as pq
import pymongo

# 配置
MONGO_URL = 'localhost'
MONGO_DB = 'taobao'
SHOPS = ['海底捞', '小龙坎']
USER = 'test'
PASSWD = 'test'

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]

# browser = webdriver.PhantomJS(service_args=['--disk-cache=true', '--load-images=false'])
browser = webdriver.Chrome()

browser.maximize_window()

wait = WebDriverWait(browser, 30)

def login():
    print('【正在登录……】')
    try:
        browser.get('https://login.taobao.com')
        time.sleep(2)
        # 切换账号密码登录
        button = wait.until(EC.element_to_be_clickable((By.ID, 'J_Quick2Static')))
        button.click()
        time.sleep(2)
        # 输入账号，输入不能太快，不然需要验证
        user = wait.until(EC.presence_of_element_located((By.ID, 'TPL_username_1')))
        for letter in USER:
            time.sleep(random.random())
            user.send_keys(letter)
        time.sleep(2)
        # 输入密码，输入不能太快，不然需要验证
        passwd = wait.until(EC.presence_of_element_located((By.ID, 'TPL_password_1')))
        for letter in PASSWD:
            time.sleep(random.random())
            passwd.send_keys(letter)
        time.sleep(2)
        # 点击登录
        log = wait.until(EC.element_to_be_clickable((By.ID, 'J_SubmitStatic')))
        log.click()
        time.sleep(1)
        # 判断是否登录成功
        if browser.title == '淘宝网 - 淘！我喜欢':
            login()
        else:
            print('【登录成功……】')
            # 记录上次登录
            db['login'].insert({ 'ts': time.time() })
    except TimeoutException:
        login()

def get_shop(shop):
    print(' ')
    print('【正在搜索店铺：%s……】' % shop)
    try:
        # 进行店铺搜索
        browser.get('https://shopsearch.taobao.com/search?app=shopsearch')
        # 输入关键词
        input_box = wait.until(EC.presence_of_element_located((By.ID, 'q')))
        input_box.send_keys(shop)
        # 点击搜索
        button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, '#J_SearchForm > button')))
        button.click()
        # 获取商铺链接
        link = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, '#list-container .list-item li.list-info > h4 > a')))
        path = link.get_attribute('href')
        # 打开商铺所有商品列表第一页
        page = 1
        js = "window.open('%scategory.htm?pageNo=%d')" % (path, page)
        browser.execute_script(js)
        browser.switch_to_window(browser.window_handles[1])
        all = False
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#J_ShopSearchResult > div')))
        while not all:
            # 获取所有列表
            lis = browser.find_elements(By.CSS_SELECTOR, '#J_ShopSearchResult .skin-box-bd div.J_TItems dl')
            print(' ')
            print('【第%d页共%d条结果】' % (page, len(lis)))
            for item in lis:
                get_product(shop, item)
            page += 1
            browser.get('%scategory.htm?pageNo=%d' % (path, page))
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#J_ShopSearchResult > div')))
            try:
                # 判断是否获取完毕，获取完毕将能得到p.item-not-found元素，否则报错
                browser.find_element(By.CSS_SELECTOR, '#J_ShopSearchResult .skin-box-bd div.no-result-new p.item-not-found')
                all = True
            except Exception as e:
                # 报错，证明还没获取完毕
                print('【正在翻页……】')
        # 该店铺获取完毕，关闭窗口
        browser.close()
        browser.switch_to_window(browser.window_handles[0])
    except TimeoutException:
        get_shop(shop)

def get_product(shop, item):
    print(' ')
    print(time.strftime('>>>>>>>> %Y-%m-%d %H:%M:%S', time.localtime()))
    try:
        # 商品概述
        product = {
            'title': item.find_element(By.CSS_SELECTOR, '.detail a').text,
            'price': item.find_element(By.CSS_SELECTOR, '.detail .attribute .cprice-area .c-price').text,
            'deal': item.find_element(By.CSS_SELECTOR, '.detail .attribute .sale-area .sale-num').text,
            'comt': item.find_element(By.CSS_SELECTOR, '.rates div.title h4 a').text.split(': ')[1]
        }
        # 商品详情
        link = item.find_element(By.CSS_SELECTOR, '.title a')
        product['href'] = link.get_attribute('href')
        print('【链接】', product['href'])
        link.click()
        browser.switch_to_window(browser.window_handles[2])
        print('【标题】', browser.title)
        time.sleep(5)
        html = pq(browser.page_source)
        if browser.title.endswith('天猫'):
            product['m_sell'] = html.find('#detail .tm-ind-panel .tm-ind-sellCount .tm-count').text()
            product['t_comt'] = html.find('#detail .tm-ind-panel .tm-ind-reviewCount .tm-count').text()
        else:
            product['m_sell'] = html.find('#detail .tb-meta .tb-counter .tb-sell-counter strong').text()
            product['t_comt'] = html.find('#detail .tb-meta .tb-counter .tb-rate-counter strong').text()
        # 商品评论
        browser.close()
        browser.switch_to_window(browser.window_handles[1])
        # 储存
        db[shop].insert(product)
        print('【保存成功】', product)
    except TimeoutException:
        get_shop(shop)

def main():
    try:
        last_log = db['login'].find_one()
        # 随机登录一次
        if time.time() - last_log['ts'] > 60 * 60 * random.randint(3, 5):
            login()
            time.sleep(20)
        for shop in SHOPS:
            get_shop(shop)

    except Exception as e:
        print(e.args)

    finally:
        browser.quit()

if __name__=='__main__':
    main()