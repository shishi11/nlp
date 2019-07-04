# -*- coding: utf-8 -*-
# @Date    : 2017/3/5 18:51
# @Author  : Wilson
# @Version : 0.8

# 导入库文件
import requests
from bs4 import BeautifulSoup
import time
import re


# 网络请求的请求头
# headers = {
#         'User-Agent': '',
#         'cookie': ''
#         }
class Baiduzhidao_spider():
    url = 'https://zhidao.baidu.com/search?word=%s&ie=utf-8&site=-1&sites=0&date=0&pn=%s'
    # 构造爬取函数
    def get_page(self,url,keyword, data=None):
        # 获取URL的requests
        wb_data = requests.get(url)
        wb_data.encoding = ('gbk')
        soup = BeautifulSoup(wb_data.text, 'lxml')

        # 定义爬取的数据
        titles = soup.select('a.ti')
        answer_times = soup.select('dd.dd.explain.f-light > span:nth-of-type(1)')
        answer_users = soup.select('dd.dd.explain.f-light > span:nth-of-type(2) > a')
        answers = soup.select('dd.dd.explain.f-light > span:nth-of-type(3) > a')
        agrees = soup.select('dd.dd.explain.f-light > span.ml-10.f-black')
        answer_summarys=soup.select('dd.answer')
        # agrees.encoding = ('gbk')
        result=[]
        # 在获取到的数据提取有效内容
        if data == None:
            i=0
            for title, answer_time, answer_user, answer, agree,answer_summary in zip(titles, answer_times, answer_users, answers, agrees,answer_summarys):
                data = [
                    title.get_text(),
                    answer_time.get_text(),
                    answer_user.get_text(),
                    answer.get_text(),
                    agree.get_text().strip(),
                    answer_summary.get_text(),
                    keyword
                ]
                i+=1
                print(i,keyword,data)
                result.append(data)
                # saveFile(data)
        return result

    # 迭代页数
    def get_more_page(self,keyword,start, end):
        result=[]
        for one in range(start, end, 10):
            result.extend(self.get_page(self.url % (keyword,str(one)),keyword))
            time.sleep(2)
        return result
    def getQA(self,keyword,pages):
        return self.get_more_page(keyword,0,int(pages) * 10)
    # 定义保存文件函数
    # def saveFile(data):
    #     path = "./1233.txt"
    #     file = open(path, 'a')
    #     file.write(str(data))
    #     file.write('\n')
    #     file.close()


# 主体
# 定义爬取关键词、页数
keyword ='故宫博物院%20占地面积'# input('请输入关键词\n')
pages = '2'#input('请输入页码\n')

# 定义将要爬取的URL

# spider=Baiduzhidao_spider()
# # 开始爬取
# spider.get_more_page(keyword,0, int(pages) * 10)

