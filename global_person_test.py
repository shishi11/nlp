# -*- coding: utf-8 -*
import cgi
import pickle
import re
import time

import jsonpath as jsonpath
import pymysql
import requests
import json
import logging
from collections import defaultdict
import textProcess
from bs4 import BeautifulSoup
from zhon.hanzi import punctuation
import zhon.cedict.all as cedit_all
from py2neo import Graph, Node, Relationship, NodeMatcher,PropertyDict
import progressbar


logging.basicConfig(level=logging.INFO)  # ,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging = logging.getLogger(__name__)


class PersonKG():
    url = 'http://10.122.141.12:9006/similar'
    threshlod=1
    def get_sim(self, something):

        r = requests.post(self.url, json={"ck": "synonym", "synonym_word": something, "synonym_selectedMode": "auto",
                                          "homoionym_word": "", "homoionym_selectedMode": "auto", "homoionym_num": ""})
        json = r.json()
        result = json['detail']['res']['synonym']
        return result

    def parsePlaces(self,nslist):
        placelist = []
        placelist_ = []
        placelist_fullname=[]
        for ns in nslist:
            if (self.place_dict.get(ns)):
                samename = self.place_dict.get(ns)
                for p in samename:
                    place = self.place_index.get(p['id'])
                    placelist.append(place)
                    # if (place['name'] == '常熟市'):
                    #     print(place)
                    if place['name']==ns:
                        #如果名称与全名相对应
                        placelist_fullname.append(place)

                    if place['level'] != '-1' :
                        self.addplace(placelist_, place)
        # logging.info(str(placelist))
        # logging.info(str(placelist_))
        return self.filter_ai_global(placelist, placelist_,placelist_fullname)

    def parseDoc_global(self,doc):
        t = time.time()
        nslist = self.tp.posseg(doc, ['nh'])
        logging.info('%d nhlist:%s' % (time.time() - t, str(nslist)))
        return self.parsePlaces(nslist)

    def filter_ai_global(self,placelist,placelist_,placelist_fullname):
        placelist_sure = defaultdict(set)
        for p in placelist_fullname:
            placelist_sure[p['level']].add(p['name'])
            self.complete_place(placelist_sure, p)

        for p in placelist:
            # if(p['name']=='北仑区'):
            #     print(placelist_sure)
            if p['name'] in placelist_sure[p['level']]:continue
            p2parent = self.place_index.get(p['pid'])
            #一种省直接对区级市，江苏常熟
            if p2parent==None:
                placelist_sure[p['level']].add(p['name'])
                continue
            if p2parent in placelist:
                placelist_sure[p['level']].add(p['name'])
                # placelist_sure[p2parent['level']].add(p2parent['name'])
                self.complete_place(placelist_sure,p)
                continue
            if placelist_.count(p2parent)>self.threshlod and placelist.count(p)<placelist_.count(p2parent):
                placelist_sure[p['level']].add(p['name'])
                # placelist_sure[p2parent['level']].add(p2parent['name'])
                self.complete_place(placelist_sure, p)
                placelist.append(p2parent)#加到明确的c列表
                continue
            if placelist.count(p)==len([p_ for p_ in placelist if p_['level']==p['level']]) and len([p_ for p_ in placelist if p_['level']==p2parent['level']])==0:
                placelist_sure[p['level']].add(p['name'])
                # placelist_sure[p2parent['level']].add(p2parent['name'])
                self.complete_place(placelist_sure, p)
                placelist.append(p2parent)  # 加到明确的c列表

        return placelist_sure
    def complete_place(self,placelist_sure,p):
        p2parent = self.place_index.get(p['pid'])
        if p2parent == None:
            # placelist_sure[p['level']].add(p['name'])
            return placelist_sure
        placelist_sure[p2parent['level']].add(p2parent['name'])
        return self.complete_place(placelist_sure,p2parent)

    def addplace(self,placelist_,place):
        if place==None:return placelist_
        place_=self.place_index.get(place['pid'])
        if place['level'] == '-1' :
            placelist_.append(place)
            return placelist_
        else:
            placelist_.append(place)
            self.addplace(placelist_,place_)
        return placelist_

    def parseDoc(self, doc):
        t=time.time()
        nslist = self.tp.posseg(doc, ['ns'])
        logging.info('%d nslist:%s' % (time.time()-t,str(nslist)))
        citylist = []
        districtlist = []
        provincelist = []
        citylist_ = []
        provincelist_ = []
        for ns in nslist:
            if (self.city_dict.get(ns)):
                samename = self.city_dict.get(ns)
                for c in samename:
                    city = self.city_index.get(c['id'])
                    citylist.append(city)
                    # 补充上层地区
                    province_ = self.province_index.get(city['pid'])
                    provincelist_.append(province_)

            if (self.district_dict.get(ns)):
                samename = self.district_dict.get(ns)
                for d in samename:
                    district = self.district_index.get(d['id'])
                    districtlist.append(district)
                    city_ = self.city_index.get(district['pid'])
                    citylist_.append(city_)
                    province_ = self.province_index.get(city_['pid'])
                    provincelist_.append(province_)

            if (self.province_dict.get(ns)):
                samename = self.province_dict.get(ns)
                for p in samename:
                    province = self.province_index.get(p['id'])
                    provincelist.append(province)

        return self.filter_ai(provincelist,districtlist,citylist,provincelist_,citylist_)

    def filter_ai(self, provincelist, districtlist, citylist,provincelist_,citylist_,threshlod=1):
        # 如何根据地理关系，对位置进行过滤呢？
        # 1.如果d的上级有明确的C，则d和c都可以确认 ok
        # 2.如果c的上级有明确的P，则c和p都可以确认 ok
        # 3.如果只有一个明确的d，且没有非明确的其他的c，d被取消
        # 4.如果只有一个明确的c，且没有非明确的其他的p，也没有非明确同一个c ，c被取消
        # 5.如果有多个不同的d，指向同一个非确定c，则d和c都可确认ok
        # 6.如果有多个明确的c，指向同一个非确定的p，则c和p都可以确认。ok
        # 7.如果只有多个相同的d，？？？？？非确认
        # 8.如果只有多个相同的确认的c，？？？？非确认
        # 9.多个相同的确认的p，可确认p
        #10.如果d的c的p是确认的，中间没有明确的c，只有一个d，就只能确认，有多个d,但只有一个这样的d，不能确认

        districtlist_sure=set()
        citylist_sure = set()
        provincelist_sure = set()

        for d in districtlist:
            d2c=self.city_index.get(d['pid'])
            if d2c in citylist:
                districtlist_sure.add(d['name'])
                citylist_sure.add(d2c['name'])
                continue
            if citylist_.count(d2c)>threshlod and districtlist.count(d)<citylist_.count(d2c):
                districtlist_sure.add(d['name'])
                citylist_sure.add(d2c['name'])
                citylist.append(d2c)#加到明确的c列表
                continue
            # c2p=self.province_index.get(d2c['pid'])
            if districtlist.count(d)==len(districtlist) and len(citylist)==0:
                districtlist_sure.add(d['name'])
                citylist_sure.add(d2c['name'])
                citylist.append(d2c)  # 加到明确的c列表


        for c in citylist:
            c2p=self.province_index.get(c['pid'])
            if c2p in provincelist:
                citylist_sure.add(c['name'])
                provincelist_sure.add(c2p['name'])
                continue
            if provincelist_.count(c2p)>threshlod and citylist.count(c)<provincelist_.count(c2p):
                citylist_sure.add(c['name'])
                provincelist_sure.add(c2p['name'])
                provincelist.append(c2p)
                continue
            if citylist.count(c)==len(citylist) and len(provincelist)==0:
                citylist_sure.add(c['name'])
                provincelist_sure.add(c2p['name'])
                provincelist.append(c2p)
                continue
        for p in provincelist:
            #只提到省
            if provincelist.count(p) == len(provincelist):
                provincelist_sure.add(p['name'])
                continue
            if provincelist.count(p)>threshlod:
                provincelist_sure.add(p['name'])


        # logging.info(str(districtlist_sure))
        # logging.info(str(citylist_sure))
        # logging.info(str(provincelist_sure))

        return citylist_sure,districtlist_sure,provincelist_sure


    # 暂时没有国的
    def getPlace(self, s, complete=True):
        city, district, province,city_,province_ = None, None, None,None,None
        if (self.city_dict.get(s)):
            # print('find city ', self.city_dict.get(s, set()))
            # print(self.city_index.get(self.city_dict.get(s, set())['id']))
            samename=self.city_dict.get(s)
            for c in samename:
                city = self.city_index.get(c['id'])
            # 补充上层地区
            if complete and city:
                province_ = self.province_index.get(city['pid'])

        if (self.district_dict.get(s)):
            # print('find district ', self.district_dict.get(s, set()))
            # print(self.district_index.get(self.district_dict.get(s, set())['id']))
            district = self.district_index.get(self.district_dict.get(s, set())['id'])
            if complete and district:
                city_ = self.city_index.get(district['pid'])

                province_ = self.province_index.get(city_['pid'])


        if (self.province_dict.get(s)):
            # print('find province ', self.province_dict.get(s, set()))
            # print(self.province_index.get(self.province_dict.get(s, set())['id']))
            province = self.province_index.get(self.province_dict.get(s, set())['id'])
        return city, district, province,city_,province_




    def connect_db(self):
        return pymysql.connect(host='192.168.1.101',
                               port=3306,
                               user='root',
                               password='',
                               database='xinhua',
                               charset='utf8')

    def query_city_name(self, sql_str):
        logging.info(sql_str)
        con = self.connect_db()
        cur = con.cursor()
        cur.execute(sql_str)
        rows = cur.fetchall()
        cur.close()
        con.close()
        return rows

    def __init__(self):

        # self.graph.delete_all()

        load_file = open('./mod/person_dict.bin', 'rb')
        self.person_dict = pickle.load(load_file)
        load_file = open('./mod/person_index.bin', 'rb')
        self.person_index = pickle.load(load_file)

        logging.info('person count %d,person name count:%s' % (len(self.person_index), len(self.person_dict)))
        # self.threshlod=threshold
        # self.tp = textProcess.TextProcess()
        #
        load_file = open('./mod/baidu_person.bin', 'rb')
        # # self.baidu_person=dict()
        self.baidu_person=pickle.load(load_file)
        logging.info('baidu person count %d' % (len(self.baidu_person)))

        # self.zhishi_place=dict()


    def gen(self):
        # 先定义一个进度条
        # http://blog.useasp.net/
        self.pbar = progressbar.ProgressBar(maxval=100, \
                                            widgets=[progressbar.Bar('=', '[', ']'), ' ', \
                                                     progressbar.Percentage()])
        self.graph = Graph("http://192.168.1.100:7474", username="neo4j", password='admin')
        matcher=NodeMatcher(self.graph)
        # persons=self.graph.nodes.match('人员')
        neo_persons=list(matcher.match('人员'))
        # persons=[person.get('name') for person in neo_persons]
        logging.info('neo persons is %d'% len(neo_persons))

        person_all_dict = defaultdict(list)
        personIndex = dict()

        self.pbar.start()
        for person in self.pbar(neo_persons):
            person_name=person.get('name')
            # if person_all_dict[person_name]:
            #     logging.info(str(person_all_dict[person_name]))
            if(len(person_name)<4 and person.get('国籍')=='中国'):
                None
            else:
                aliasPerson=self.get_sim(person_name)
                baiduPersonNames = self.getBaiduSame(person_name)
            person_all = set([person_name]).union(set(aliasPerson)).union(set(baiduPersonNames))
            #name: 马国强国籍: 中国类别: 国内政要职务: 湖北省委副书记职务简称: 武汉市委书记英文名: maguoqiang
            personIndex[person.identity]={'name':person.get('name'),'nationality':person.get('国籍'),'catalog':person.get('类别'),'job':person.get('职务'),'job1':person.get('职务简称'),'ename':person.get('英文名')}
            for c in person_all :
                if c !=None:
                    #出现重名情况、一人多职的情况
                    person_all_dict[c].append({'id': person.identity})
            # self.pbar.update(i/len(neo_persons)*100)
        self.pbar.finish()
        logging.info('person count %d,all_person count %d' % (len(personIndex), len(person_all_dict)))
        fou = open('./mod/person_dict.bin', 'wb')
        pickle.dump(person_all_dict, fou)
        fou.close()
        fou = open('./mod/person_index.bin', 'wb')
        pickle.dump(personIndex, fou)
        fou.close()
        fou = open('./mod/baidu_person.bin', 'wb')
        pickle.dump(self.baidu_person, fou)
        fou.close()

    def getBaiduSame(self,person_name):
        if self.baidu_person.get(person_name):
           # logging.info('find %s from baidu_place' % place )
           return self.parseHtml(person_name, self.baidu_person.get(person_name))


        url='https://baike.baidu.com/item/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
            'Accept': 'text / html, application / xhtml + xml, application / xml;q = 0.9,image/webp, * / *;q = 0.8',
            'Accept-Language': 'zh-CN, zh;q = 0.9'
        }
        try:
            wb_data = requests.get(url+person_name,headers=headers,allow_redirects=True)
            wb_data.encoding='utf-8'
        except:
            return []
        content = wb_data.text
        return self.parseHtml(person_name,content)

    def parseHtml(self,person_name,content):

        clear =  re.compile('<script[^>]*?>[\\s\\S]*?<\\/script>', re.I)#re.compile('<\s*script[^>]*>[^<]*<\s*/\s*script\s*>', re.I)

        content = clear.sub("", content)
        # content=str(content,encoding='utf-8')
        # logging.info(content)
        # self.save_db(place,content)
        self.baidu_person[person_name]=content

        soup = BeautifulSoup(content, 'html.parser')
        [script.extract() for script in soup.findAll('script')]
        # s=soup.text

        try:
            title_node = soup.find('dd', class_='lemmaWgt-lemmaTitle-title').find('h1').text
        except:
            return []
        '''
        <dt class="basicInfo-item name">别&nbsp;&nbsp;&nbsp;&nbsp;名</dt>
        <dd class="basicInfo-item value">
        三袁故里、百湖之县
        </dd>
        '''
        def parse_alias(alias):
            alias=self.tp.remove_noisy(alias)
            if alias[-1]=='等': alias=alias[:-1]
            alias=re.sub(r'[%s|\/,;]' % punctuation,'、',alias)
            return alias.split('、')
        samenames =[title_node]# soup.find('dt', class_='basicInfo-item name', text='中文名称').find_next('dd').text.strip().split('、')
        try:
            alias=soup.find('dt', class_='basicInfo-item name', text='别    名').find_next('dd').text.strip()
            # alias
            samenames.extend(parse_alias(alias))
        except:
            None
        try:
            alias=soup.find('dt', class_='basicInfo-item name', text='外文名').find_next('dd').text.strip()
            samenames.extend(alias.split('、'))
        except:
            None
        # samenames=samenames1.extend(samenames2).extend(samenames3)
        # logging.info(samenames)
        return samenames
    '''
    失败，有字符集问题
    '''
    def save_db(self,place,content):
        logging.info(content)
        con = self.connect_db()
        con.autocommit(True)
        cur = con.cursor()
        cur.execute("insert into baidu_place values(%s,%s)",(place,content))
        cur.close()
        con.close()
        return

    def getZhishi(self,place):
        if self.person_dict.get(place):
           logging.info('find %s from zhishi_place' % place )
           return self.baidu_place.get(place)


        url='http://zhishi.me/api/entity/%s?property=infobox'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
            'Accept': 'text / html, application / xhtml + xml, application / xml;q = 0.9,image/webp, * / *;q = 0.8',
            'Accept-Language': 'zh-CN, zh;q = 0.9'
        }
        try:
            wb_data = requests.get(url % place,headers=headers,allow_redirects=True)
            wb_data.encoding='utf-8'
            content = wb_data.json()
            logging.info(str(content))
            ret1 = jsonpath.jsonpath(content, "$..'别称：'")
            logging.info(str(ret1[0]))
            if ret1:
                return ret1[0][0].split('、')

        except:
            return []
    '''
    这个基本不可用，比较老且不全
    '''
    def getXLORE(self,place):
        url ='http://api.xlore.org/query?instances='
        url='http://api.xlore.org/relations?instance=%s&relation=%s'
        try:
            wb_data = requests.get(url % ('任正非','职务'),allow_redirects=True)
            wb_data.encoding='utf-8'
            content = wb_data.json()
            logging.info(str(content))
            return content

        except:
            return []
    def genLTP_Dict(self):
        with open('./resources/ltp_person.dict','w',encoding='utf-8') as f:
            for p in self.person_dict:
                # if p in cedit_all:
                    pattern = ".*?[\u4E00-\u9FA5|·]"

                    pat = re.compile(pattern)
                    if pat.match(p):
                        f.write(p+'\t'+'nh'+'\n')


    def test(self):
        # print(self.get_sim('本拉登'))
        s = '习近平在重庆调研时强调，创新、协调、绿色、开放、共享的发展理念，一带一路是在深刻总结国内外发展经验教训、分析国内外发展大势的基础上形成的，凝聚着对经济社会发展规律的深入思考，体现了“十三五”乃至更长时期我国的发展思路、发展方向、发展着力点。'

        # print(self.parseDoc_global('常熟市'))
        rows = self.query_city_name(
            'SELECT DISTINCT file_uuid,txt FROM e20190313 GROUP BY file_uuid,txt LIMIT 6,1')
        for row in rows:
            title = row[0]
            detail = row[1]
            logging.info(str(title) + detail)
            t = time.time()
            pl = self.parseDoc_global(str(title) + detail)
            logging.info('%s ' % str(pl))
            logging.info('cost:%d' % (time.time() - t))
    logging.info('-' * 15)

p = PersonKG()
# p.genLTP_Dict()
# p.gen()
# s='习近平在重庆调研时强调，创新、协调、绿色、开放、共享的发展理念，一带一路是在深刻总结国内外发展经验教训、分析国内外发展大势的基础上形成的，凝聚着对经济社会发展规律的深入思考，体现了“十三五”乃至更长时期我国的发展思路、发展方向、发展着力点。'
# g.parseDoc(s)
# p.test()
# g.getBaiduSame('连云港')
print(p.getBaiduSame('黄文秀'))