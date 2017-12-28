import re, time, random, sys
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from pyquery import PyQuery as pq
import pymongo

# 配置
MONGO_URL = 'localhost'
MONGO_DB = 'taobao'
SHOPS = ['海底捞', '小龙坎']
COMMENT_PAGE = 5
USER = 'test'
PASS = 'test'

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
        for letter in PASS:
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
    except TimeoutException:
        login()

def login_js():
    print('【正在登录……】')
    browser.get('https://login.taobao.com')
    time.sleep(5)
    js = '''document.getElementById('TPL_username_1').value = '%s';
        document.getElementById('TPL_password_1').value = '%s';
        var event = new MouseEvent('click', {
            view: window,
            bubbles: true,
            cancelable: true
        });
        var cb = document.getElementById('J_SubmitStatic'); 
        var cancelled = !cb.dispatchEvent(event);
        ''' % (USER, PASS)
    browser.execute_script(js)
     # 判断是否登录成功
    if browser.title == '淘宝网 - 淘！我喜欢':
        print('【登录失败……】')
        # 输入密码，输入不能太快，不然需要验证
        passwd = wait.until(EC.presence_of_element_located((By.ID, 'TPL_password_1')))

        for letter in PASS:
            time.sleep(0.05)
            passwd.send_keys(letter)
        browser.implicitly_wait(20)

        nocaptcha = browser.find_element_by_id("nocaptcha")
        if nocaptcha.text != "":
            dragger = browser.find_element_by_class_name('nc_iconfont');
            action = ActionChains(browser)
            action.click_and_hold(dragger).perform()  #鼠标左键按下不放
            for index in range(10):
                try:
                    action.move_by_offset(20, 0).perform() #平行移动鼠标
                except Exception:
                    break
                #action.reset_actions()
                time.sleep(0.05)  #等待停顿时间
        
        # 点击登录
        log = wait.until(EC.element_to_be_clickable((By.ID, 'J_SubmitStatic')))
        log.click()
        time.sleep(1)

    else:
        print('【登录成功……】')

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
        # 删除旧数据
        db[shop].delete_many({})
        # 打开商铺所有商品列表第一页
        page = 1
        js = "window.open('%scategory.htm?pageNo=%d')" % (path, page)
        browser.execute_script(js)
        browser.switch_to_window(browser.window_handles[1])
        all = False
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#J_ShopSearchResult > div')))
        while not all:
            # 获取所有列表
            lis = browser.find_elements(By.CSS_SELECTOR, '#J_ShopSearchResult .skin-box-bd div.J_TItems dl .title a')
            print(' ')
            print('【第%d页共%d条结果】' % (page, len(lis)))
            count = 0
            for item in lis:
                print(' ')
                print(time.strftime('>>>>>>>> %Y-%m-%d %H:%M:%S No.' + str(count + 1), time.localtime()))
                if (count + 1) % 4 == 0:
                    browser.execute_script("window.scrollTo(0, 315)")
                get_product(shop, count)
                count += 1
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
        print('【获取店铺超时，重试……】')
        get_shop(shop)

def get_product(shop, count):
    try:
        item = browser.find_elements(By.CSS_SELECTOR, '#J_ShopSearchResult .skin-box-bd div.J_TItems dl')[count]
        # 商品概述
        product = {
            'title': item.find_element(By.CSS_SELECTOR, '.detail a').text,
            'price': item.find_element(By.CSS_SELECTOR, '.detail .attribute .cprice-area .c-price').text,
            'deal': item.find_element(By.CSS_SELECTOR, '.detail .attribute .sale-area .sale-num').text,
            'comt': item.find_element(By.CSS_SELECTOR, '.rates div.title h4 a').text.split(': ')[1],
            'pic': item.find_element(By.CSS_SELECTOR, '.photo img').get_attribute('src')
        }
        # 商品详情
        link = item.find_element(By.CSS_SELECTOR, '.title a')
        product['href'] = link.get_attribute('href')
        product['pid'] = parse_qs(urlparse(product['href']).query)['id'][0]
        print('【链接】', product['href'])
        
        js = '''var a = document.querySelectorAll('#J_ShopSearchResult .skin-box-bd div.J_TItems dl .title a');
        a[%d].click();
        ''' % count
        browser.execute_script(js)

        browser.switch_to_window(browser.window_handles[2])
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#J_Detail #J_Reviews div.rate-toolbar div.rate-sort span.tm-current')))
        print('【标题】', browser.title)
        if browser.title.endswith('天猫'):
            product['m_sell'] = browser.find_element(By.CSS_SELECTOR, '#detail .tm-ind-panel .tm-ind-sellCount .tm-count').text
            product['t_comt'] = browser.find_element(By.CSS_SELECTOR, '#detail .tm-ind-panel .tm-ind-reviewCount .tm-count').text
        else:
            product['m_sell'] = browser.find_element(By.CSS_SELECTOR, '#detail .tb-meta .tb-counter .tb-sell-counter strong').text
            product['t_comt'] = browser.find_element(By.CSS_SELECTOR, '#detail .tb-meta .tb-counter .tb-rate-counter strong').text
        # 储存
        db[shop].insert(product)
        print('【保存商品成功】', product)
        # 删除旧评论
        db[shop + '_' + product['pid']].delete_many({})
        # 商品评论
        time.sleep(5)
        # sort_item = browser.find_element(By.CSS_SELECTOR, '#J_Detail #J_Reviews div.rate-toolbar div.rate-sort span.tm-current')
        # sort_item.click()
        # sort = browser.find_element(By.CSS_SELECTOR, '#J_Detail #J_Reviews div.rate-toolbar div.rate-sort ul li.tm-r-time')
        # sort.click()
        js = '''var sort = document.querySelector('#J_Detail #J_Reviews div.rate-toolbar div.rate-sort ul li.tm-r-time')
        sort.click()
        '''
        browser.execute_script(js)
        page = 1
        all = False
        while not all and page <= COMMENT_PAGE:
            # 获取评论
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#J_Reviews div.rate-grid table tbody')))
            time.sleep(5)
            lis = browser.find_elements(By.CSS_SELECTOR, '#J_Reviews .rate-grid table tbody td.tm-col-master')
            print('【评论第%d页共%d条】' % (page, len(lis)))
            for item in lis:
                get_comment(shop, product['pid'], item)
            paginator = browser.find_element(By.CSS_SELECTOR, '#J_Detail #J_Reviews div.rate-page div.rate-paginator')
            if paginator.find_elements(By.CSS_SELECTOR, 'span')[-1].text is '下一页>>':
                all = True
            else:
                browser.execute_script("window.scrollTo(0, document.body.clientHeight/2.2)")
                time.sleep(2)
                page += 1
                if (page <= COMMENT_PAGE):
                    print('【正在翻评论……】')
                # paginator.find_elements(By.CSS_SELECTOR, 'a')[-1].click()
                js = '''var a = document.querySelectorAll('#J_Detail #J_Reviews div.rate-page div.rate-paginator a');
                a[a.length - 1].click()
                '''
                browser.execute_script(js)
        browser.close()
        browser.switch_to_window(browser.window_handles[1])
    except TimeoutException:
        browser.quit()
        print('【获取商品超时，重试……】')
        get_shop(shop)

def get_comment(shop, p_id, item):
    try:
        comment = {
            'comment': item.find_element(By.CSS_SELECTOR, '.tm-rate-content .tm-rate-fulltxt').text,
            'time' : item.find_element(By.CSS_SELECTOR, '.tm-rate-date').text
        }
        # 储存
        db[shop + '_' + p_id].insert(comment)
        print('【保存评论成功】', comment)
    except TimeoutException:
        browser.quit()
        print('【获取商品超时，重试……】')
        get_shop(shop)

def main():
    try:
        login_js()
        time.sleep(10)
        for shop in SHOPS:
            get_shop(shop)

    except Exception as e:
        print(e.args)

    finally:
        browser.quit()

if __name__=='__main__':
    main()