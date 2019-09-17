#!/usr/bin/env python3
# coding: utf-8
# File: baidubaike.py
# Author: lhy
# Date: 18-3-8
import pprint
import re
from urllib import request
from lxml import etree
from urllib import parse
import redis




class BaiduBaike():
    def __init__(self):
        self.red=None
        try:
            pool = redis.ConnectionPool(host='192.168.1.101', port=6379, db=1,decode_responses=True)
            self.red = redis.Redis(connection_pool=pool)

        except :
            print('ssss')
            pass
        pass

    def get_html(self, url):
        #这里进行缓存
        if self.red:
            if self.red.exists(url):
                return self.red.get(url)
            else:
                html=request.urlopen(url).read().decode('utf-8').replace('&nbsp;', '')
                self.red.set(url,html)
                return html
        return request.urlopen(url).read().decode('utf-8').replace('&nbsp;', '')

    def info_extract_baidu_abbr(self, word):  # 百度百科
        url = "http://baike.baidu.com/item/%s" % parse.quote(word)
        print(url)
        selector = etree.HTML(self.get_html(url))
        info_list = list()
        info_list.append(self.extract_baidu(selector))
        info_list[0]['link']=url

        polysemantics = self.checkbaidu_polysemantic(selector)
        if polysemantics:
            info_list += polysemantics
        infos = [info for info in info_list if len(info) > 2]

        return infos

    def info_extract_baidu_url(self,url):
        selector = etree.HTML(self.get_html(url))
        info_list = list()
        info_list.append(self.extract_baidu(selector, abbr=True))
        info_list[0]['link'] = url
        polysemantics = self.checkbaidu_polysemantic(selector)
        if polysemantics:
            info_list += polysemantics
        infos = [info for info in info_list if len(info) > 2]
        return infos

    def info_extract_baidu(self, word):  # 百度百科
        url = "http://baike.baidu.com/item/%s" % parse.quote(word)
        print(url)
        selector = etree.HTML(self.get_html(url))
        info_list = list()
        info_list.append(self.extract_baidu(selector,abbr=True))
        info_list[0]['link']=url
        polysemantics = self.checkbaidu_polysemantic(selector,abbr=True)
        if polysemantics:
            info_list += polysemantics
        infos = [info for info in info_list if len(info) > 2]

        return infos
    def info_extract_baidu_(self, word):  # 百度百科
        url = "http://baike.baidu.com/item/%s" % parse.quote(word)
        print(url)
        selector = etree.HTML(self.get_html(url))
        info_list = list()
        info_list.append(self.extract_baidu_(selector))
        if(info_list[0]['current_semantic']==''):
            #特珠情况
            polysemantics = self.checkbaidu_polysemantic_(selector)
        else:
            polysemantics = self.checkbaidu_polysemantic(selector)
        if polysemantics:
            info_list += polysemantics
        infos = [info for info in info_list if len(info) > 2]

        return infos
    def extract_baidu_(self, selector):
        info_data = {}
        if selector.xpath('//h2/text()'):
            info_data['current_semantic'] = selector.xpath('//h2/text()')[0].replace('    ', '').replace('（','').replace('）','')
        else:
            info_data['current_semantic'] = ''
        if info_data['current_semantic'] == '目录':
            info_data['current_semantic'] = ''

        info_data['tags'] = [item.replace('\n', '') for item in selector.xpath('//span[@class="taglist"]/text()')]
        if selector.xpath("//div[starts-with(@class,'basic-info')]"):
            for li_result in selector.xpath("//div[starts-with(@class,'basic-info')]")[0].xpath('./dl'):
                attributes = [attribute.xpath('string(.)').replace('\n', '') for attribute in li_result.xpath('./dt')]
                values = [value.xpath('string(.)').replace('\n', '') for value in li_result.xpath('./dd')]
                for item in zip(attributes, values):
                    info_data[item[0].replace('    ', '')] = item[1].replace('    ', '')
            paras=[]
            para_text=''
            # pattern = re.compile('“(.*?)”')
            if selector.xpath("//div[starts-with(@class,'para')]"):
                for para in selector.xpath("//div[starts-with(@class,'para')]"):
                    # paras.append(para.text)
                    if para.text:
                        # para_text=para_text+para.text
                        paras.append(para.text)

                # info_data['keywords']=anse.extract_tags(para_text, topK=20, withWeight=False)+paras

            #计算后面的地点、职位、最高词频等值

            #补充元数据
            info_data['desc']=selector.xpath('//meta[@name="description"]/@content')
            # info_data['keywords']=selector.xpath('//meta[@name="keywords"]/@content')
            info_data['detail']=paras



        return info_data

    # def extract_baidu(self, selector):

    def extract_baidu(self, selector,abbr=False):
        info_data = {}
        if abbr:
            info_data['selector']=selector
        if selector.xpath('//h2/text()'):
            info_data['current_semantic'] = selector.xpath('//h2/text()')[0].replace('    ', '').replace('（','').replace('）','')
        else:
            info_data['current_semantic'] = ''
        if info_data['current_semantic'] == '目录':
            info_data['current_semantic'] = ''

        info_data['tags'] = [item.replace('\n', '') for item in selector.xpath('//span[@class="taglist"]/text()')]
        if selector.xpath("//div[starts-with(@class,'basic-info')]"):
            for li_result in selector.xpath("//div[starts-with(@class,'basic-info')]")[0].xpath('./dl'):
                attributes = [attribute.xpath('string(.)').replace('\n', '') for attribute in li_result.xpath('./dt')]
                values = [value.xpath('string(.)').replace('\n', '') for value in li_result.xpath('./dd')]
                for item in zip(attributes, values):
                    info_data[item[0].replace('    ', '')] = item[1].replace('    ', '')

        #补充元数据
        info_data['desc']=selector.xpath('//meta[@name="description"]/@content')
        info_data['keywords']=selector.xpath('//meta[@name="keywords"]/@content')

        return info_data
    def checkbaidu_polysemantic_(self, selector):
        semantics = ['https://baike.baidu.com' + sem for sem in
                     selector.xpath("//ul[starts-with(@class,'custom_dot')]/li/div/a/@href")]
        names = [name for name in selector.xpath("//ul[starts-with(@class,'custom_dot')]/li/div/a/text()")]
        info_list = []
        if semantics:
            for item in zip(names, semantics):
                selector = etree.HTML(self.get_html(item[1]))
                info_data = self.extract_baidu(selector)
                info_data['link']=item[1]
                info_data['current_semantic'] = item[0].replace('    ', '').replace('（','').replace('）','')
                if info_data:
                    info_list.append(info_data)
        return info_list
    def checkbaidu_polysemantic(self, selector,abbr=False):
        semantics = ['https://baike.baidu.com' + sem for sem in
                     selector.xpath("//ul[starts-with(@class,'polysemantList-wrapper')]/li/a/@href")]
        names = [name for name in selector.xpath("//ul[starts-with(@class,'polysemantList-wrapper')]/li/a/text()")]
        info_list = []
        if semantics:
            for item in zip(names, semantics):
                selector = etree.HTML(self.get_html(item[1]))
                info_data = self.extract_baidu(selector,abbr)
                info_data['link'] = item[1]
                info_data['current_semantic'] = item[0].replace('    ', '').replace('（','').replace('）','')
                if info_data:
                    info_list.append(info_data)
        return info_list
'''
baidu = BaiduBaike()
while(1):
    word = input('enter an word:')
    baidu.info_extract_baidu(word)
'''
if __name__ == '__main__':
    baidu = BaiduBaike()
    # pprint.pprint(baidu.info_extract_baidu('哥伦比亚共和国'))

    pprint.pprint(baidu.info_extract_baidu('朝鲜'))