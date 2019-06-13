#coding:UTF-8

#libraries needs to be installed
#selenium, pyyaml, slackclient, bs4, lxml
# and phantomjs

# get ChromeDriver from here
# https://sites.google.com/a/chromium.org/chromedriver/downloads

from __future__ import absolute_import, division, print_function

import sys
import json
import re

import datetime
import time

import urllib

from selenium import webdriver
from selenium.webdriver.support.events import EventFiringWebDriver
from selenium.webdriver.support.events import AbstractEventListener
from selenium.webdriver.support.select import Select

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from bs4 import BeautifulSoup
import json
import yaml
import os
from slackclient import SlackClient
from time import sleep

#FOR REAL USE set this to be True to hide Chrome screen
HEADLESSNESS = True

#defalut value
SLACK_TOKEN = ''
SLACK_USER_ID = ''
SLACK_CHANNEL: ''

#loading credentials
args = sys.argv
# credentials_mukai.yaml
with open(args[1],"r") as stream:
    try:
        credentials = yaml.load(stream, Loader=yaml.SafeLoader)
        globals().update(credentials)
    except yaml.YAMLError as exc:
        print(exc)

class ScreenshotListener(AbstractEventListener):
    #count for error screenshots
    exception_screenshot_count = 0

    def on_exception(self, exception, driver):
        screenshot_name = "00_exception_{:0>2}.png".format(ScreenshotListener.exception_screenshot_count)
        ScreenshotListener.exception_screenshot_count += 1
        driver.get_screenshot_as_file(screenshot_name)
        print("Screenshot saved as '%s'" % screenshot_name)

def makeDriver(*, headless=True):
    options = Options()
    if(headless):
        options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,800')
    _driver = webdriver.Chrome(options=options)
    return EventFiringWebDriver(_driver, ScreenshotListener())

def loginDesknets(driver):
    url = DN_URL

    driver.get(url)
    driver.implicitly_wait(10)

    userId_box = driver.find_element_by_name('UserID')
    pass_box = driver.find_element_by_name('_word') 
    userId_box.send_keys(DN_USERNAME)
    pass_box.send_keys(DN_PASSWORD)

    #driver.save_screenshot('0before login.png')
    #print( "saved before login" )

    #login
    driver.find_element_by_id('login-btn').click()

    #elemは特に使わないが、ページが表示されるまで待ちたいため入れている
    elem = driver.find_element_by_css_selector(".portal-cal-body")

    #インフォメーション画面遷移    
    driver.find_element_by_css_selector('#portal-content-6 > div.portal-content-titlebar > h3 > a').click()
    sleep(3)
    
    #未読を選択
    element = driver.find_element_by_xpath("//*[@id='listfrm']/div[2]/div[2]/div[1]/div[2]/div/select[2]")
    Select(element).select_by_value("1")
    sleep(3)
    
    #driver.save_screenshot('1after login.png')
    #print( "saved after login" )
    print("URL:" + driver.current_url)
    
    return driver

#インフォメーションを取得して[{title:タイトル, author:作成者, link:リンク先}, ...] の形式で返す
def getInformation(driver):
    
    trs = driver.find_element_by_xpath("//*[@id='listfrm']/div[2]/div[2]/div[3]/table").find_elements(By.TAG_NAME, "tr")
    
    driver.implicitly_wait(2)
    information_items = []
    for i in range(0,len(trs)):
       tds = trs[i].find_elements(By.TAG_NAME, "td")
       for j in range(3,len(tds)):
           if j < len(tds):
               #タイトル、リンク先
               if j == 3:
                   title = tds[j].text
                   link =  tds[j].find_element_by_tag_name("a").get_attribute("href")
               #作成者
               elif j == 4:
                  author = tds[j].text
               #期限
               elif j == 5:
                  period = tds[j].text
       information_items.append((title,author,period,link))

    #未読を既読に変更する
    #チェックボックスにチェックを入れる
    for i in range(0,len(trs)):
       tds = trs[i].find_elements(By.TAG_NAME, "td")
       tds[0].click()
    
    #既読ボタンをクリック
    driver.find_element_by_css_selector("#listfrm > div.co-actionwrap.top.jco-list-acactionwrap > div.co-actionarea.info-actionarea > input.jinfo-list-read-submit").click()
    
    return information_items


################## main starts here ##################################
if __name__ == "__main__":
    print( "【start】" + SLACK_USER_ID + " " + str(datetime.datetime.now()))
    
    sc = SlackClient(SLACK_TOKEN)

    driver = makeDriver(headless=HEADLESSNESS)
    print( 'driver created' )

    try:

        loginDesknets(driver)

        information_items = getInformation(driver)

    except:
        print("Unexpected error:", sys.exc_info()[0])
        raise
    finally:
        if HEADLESSNESS:
            driver.quit()

    for information_item in information_items:
        #title, author, link = information_item
        title, author, period, link = information_item

        print("title:%s, author:%s, period:%s, link:%s" % (title,author,period,link) )
        message = "タイトル：%s \r\n 作成者　：%s \r\n 表示期間：%s \r\n リンク先：%s" % (title, author, period, link)
        print(message)

        sc.api_call(
        "chat.postMessage",
        channel=SLACK_CHANNEL,
        text=message,
        username="desknet's NEO インフォメーション連携",
        user=SLACK_USER_ID
        )

    print( "【end  】" + SLACK_USER_ID + " " + str(datetime.datetime.now()))