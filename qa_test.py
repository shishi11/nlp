# -*- coding: utf-8 -*
import pickle

import jsonpath
import requests
from bert_serving.client import BertClient

from baiduzhidao_test import Baiduzhidao_spider
import logging
from annoy import AnnoyIndex
import numpy as np
from collections import defaultdict
# import ahocorasick

logging.basicConfig(level=logging.INFO)  # ,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging = logging.getLogger(__name__)

class QA_process():
    def __init__(self):
        self.baiduzhidao=Baiduzhidao_spider()
        load_file = open('./mod/zhishi_entity.bin', 'rb')
        self.zhishi_entity = pickle.load(load_file)
        self.bc = BertClient(ip='192.168.1.101', ignore_all_checks=True)
        self.annoyIndex = AnnoyIndex(768)
        self.annoyIndex.load('./mod/qa_index.mod')

        load_file = open('./mod/qs_dict.bin', 'rb')
        self.qa_dict = pickle.load(load_file)

    def getZhishi(self,entity):
        if self.zhishi_entity.get(entity):
           logging.info('find %s from zhishi_entity' % entity )
           return self.zhishi_entity.get(entity)

        url='http://zhishi.me/api/entity/%s?property=infobox'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
            'Accept': 'text / html, application / xhtml + xml, application / xml;q = 0.9,image/webp, * / *;q = 0.8',
            'Accept-Language': 'zh-CN, zh;q = 0.9'
        }
        try:
            wb_data = requests.get(url % entity,headers=headers,allow_redirects=True)
            wb_data.encoding='utf-8'

            content = wb_data.json()
            logging.info('request '+str(content))
            result=jsonpath.jsonpath(content, "$..'infobox'")[0]
            self.zhishi_entity[entity]=result
            fou = open('./mod/zhishi_entity.bin', 'wb')
            pickle.dump(self.zhishi_entity, fou)
            fou.close()
            return result

        except:
            logging.error('未成功取得'+entity+'属性')
            return {}

    def getAllQA(self,theme):
        #得到主题的属性
        theme_json=self.getZhishi(theme)
        logging.info(str(theme_json))
        logging.info(str(theme_json.keys()))
        properties=theme_json.keys()
        properties=[p[:-1] for p in properties]
        qa_pairs=self.baiduzhidao.getQA(theme,5)
        for p in properties:
            qa_pairs.extend(self.baiduzhidao.getQA(theme+'%20'+p,5))
        fou = open('./mod/qa_pairs.bin', 'wb')
        pickle.dump(qa_pairs, fou)
        fou.close()

    def get_sim(self, something):
        url = 'http://10.122.141.12:9006/similar'
        r = requests.post(url, json={"ck": "synonym", "synonym_word": something, "synonym_selectedMode": "auto",
                                          "homoionym_word": "", "homoionym_selectedMode": "auto", "homoionym_num": ""})
        json = r.json()
        result = json['detail']['res']['synonym']
        return result

    def selectQA(self,qa_pairs,theme):
        theme_json=self.zhishi_entity.get(theme)
        # properties = theme_json.keys()
        # properties = [p[:-1] for p in properties]
        # qs=defaultdict(set)
        qs=dict()
        #有同义词问题
        samenames=['故宫']
        samenames.append(theme)
        for qa in qa_pairs:
            for samename in samenames:
                if samename in qa[0]:
                    #要包含主题词，这是触发词
                    # t_p=qa[6].split('%20')
                    # if(len(t_p)==2):
                    #     p=t_p[1]
                    #     p_val=theme_json.get(p+'：')
                    # qs[qa[6]].add(qa[0])
                    #直接保存吧
                    qs[qa[0]]=qa
        fou = open('./mod/qs_dict.bin', 'wb')
        pickle.dump(qs, fou)
        fou.close()

        self.save_qa_vec(qs)

    def save_qa_vec(self,qs):
        #保存到问题句向量中
        q_arr=[q for q in qs]

        encodes = self.bc.encode(q_arr)
        for i,encode in enumerate(encodes):
            self.annoyIndex.add_item(i,encode)
        self.annoyIndex.build(10)
        self.annoyIndex.save('./mod/qa_index.mod')

    def anwser(self,q):
        encode = self.bc.encode([q])[0]
        restult,distance=self.annoyIndex.get_nns_by_vector(encode,1,include_distances=True)
        answer_arr = [self.qa_dict.get(q) for q in self.qa_dict]
        quest_arr = [q for q in self.qa_dict]
        if np.cos(distance)>0.8:
            logging.info(str(np.cos(distance))+quest_arr[restult[0]])
            logging.info(str(answer_arr[restult[0]][5]))
        else:
            logging.info('不知道')
            logging.info(str(np.cos(distance)) + quest_arr[restult[0]])
            logging.info(str(answer_arr[restult[0]][5]))

    def test(self):
        # self.getAllQA('故宫博物院')
        # load_file = open('./mod/qa_pairs.bin', 'rb')
        # qa_pairs = pickle.load(load_file)
        # logging.info('qa_pairs size:%d'%len(qa_pairs))
        # self.selectQA(qa_pairs,'故宫博物院')

        # qs=set(q[0] for q in qa_pairs)
        # logging.info('qs size:%d' % len(qs))
        # sorted(maybe_errors, key=lambda k: k[1], reverse=False)

        # qs=sorted(qa_pairs,key=lambda k:int(k[4]),reverse=True)
        # logging.info(str(qs[:2]))
        q='千里江山图？'
        self.anwser(q)



qa=QA_process()
qa.test()