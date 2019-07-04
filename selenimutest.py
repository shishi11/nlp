# -*- coding: utf-8 -*

from selenium import webdriver
import time

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# driver = webdriver.Firefox()

chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

driver = webdriver.Chrome( chrome_options=chrome_options)
# driver.get("https://www.csdn.net/")
# driver.maximize_window()
first_handle = driver.current_window_handle
items=driver.find_elements_by_class_name('word-item')
current_handle=driver.current_window_handle
import datetime
search_date=datetime.date.today()-datetime.timedelta(days=1)
stop_date=datetime.date.today()-datetime.timedelta(days=2)
count=0
for item in items:
    print(item.text+'\n')
    if str(item.text).find(str('2019-02-28'))>-1:
        item.click()
        # driver.
        break
        # driver.switch_to.window(current_handle)
        # count=count+1
    # if count==6:break
# driver.find_element_by_class_name('word-item').click()
#
#

# driver.find_element_by_xpath('//div[text2019-03-04').click()
# driver.find_element_by_link_text(u'登录').click()
# time.sleep(1)
# all_handles = driver.window_handles
# driver.switch_to.window(all_handles[1])
# driver.find_element_by_link_text(u'帐号登录').click()
# driver.find_element_by_id("all").send_keys('shishi11@sina.com.cn')
# driver.find_element_by_id("password-number").send_keys('shishi11shifei')
# driver.find_element_by_tag_name('button').click()
# driver.find_element_by_class_name("logging").click()

# time.sleep(2)
# # driver.find_element_by_xpath("html/body/div[1]/div/div/ul/li[3]/a/span").click()
# time.sleep(4)
# driver.find_element_by_link_text(u'写博客').click()
#handles操作   allhandles数据是以列表形式进行存放的   我们使用索引进行操作
# all_handles = driver.window_handles
# driver.switch_to.window(all_handles[1])
# time.sleep(104)

#
# #因为我是用了chrome和firefox俩个浏览器  所以做了一个判断
# if driver.name == 'chrome':
#     pass
#     # driver.maximize_window()
# #     pass
# else:
# #     driver.maximize_window()
#     pass
# #鼠标移动操作
# driver.find_element_by_xpath(".//*[@id='btnStart']").click()
# s = driver.find_element_by_id('selType')
# Select(s).select_by_index(1)
# driver.find_element_by_id('txtTitle').send_keys(u'自己的原创')
#
# #切换iframe框架并使用键盘事件去进行操作  因为这个时候直接使用xpath去定位会失败所以我们需要借用tab键
# driver.switch_to.frame('xhe0_iframe')
# driver.find_element_by_xpath('html/body').send_keys(Keys.TAB)
# driver.find_element_by_xpath('html/body').send_keys(u'原文内容')
#
# driver.switch_to.default_content()
# #操控下拉框
# if driver.name == 'Chrome':
#     js = 'var q=document.body.scropllTop=10000'
#     driver.execute_script(js)
# else:
#     js = 'var q=document.documentElement.scrollTop=1000'
#     driver.execute_script(js)
#
# #复选框操作
# driver.find_element_by_xpath('.//*[@id="moreDiv"]/div/div[3]/div/div[2]/div[4]/label/i').click()
# #下拉框操作
# s1 = driver.find_element_by_id('radChl')
# Select(s1).select_by_index(6)
#
# #点击发布
# driver.find_element_by_xpath('.//*[@id="btnPublish"]').click()
