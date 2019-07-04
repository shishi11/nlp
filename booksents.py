# -*-coding:utf-8-*-
'''
取书中的句子，作成微量
从一个目录中取书
'''
import glob
import logging
import os
import pickle
import pyltp

import zhon.hanzi

from openpyxl import load_workbook
from bert_serving.client import BertClient
from annoy import AnnoyIndex
import numpy as np

from textProcess import TextProcess

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)

class BookSent():
    def __init__(self):
        self.bc=BertClient(ip='192.168.1.103',ignore_all_checks=True)
        self.splitter = pyltp.SentenceSplitter()
        self.annoyIndex=AnnoyIndex(768)
        try:
            self.annoyIndex.load('./mod/book.mod')
            load_file=open('./resources/book.bin','rb')
            self.sents=pickle.load(load_file)
            # for i,sent in enumerate(self.sents):
            #     if sent[1]=='':self.sents[i][1]='《习近平谈治国理政》第二卷'
            # fou = open('./resources/book.bin', 'wb')
            # pickle.dump(self.sents, fou)
            # fou.close()
            logger.info('%d golden sentances loaded',len(self.sents))
            logger.info('include '+str(set([sent[1] for sent in self.sents])))
        except:
            pass


    def findBook(self,sent):
        sent_encode=self.bc.encode([sent])[0]
        result,distance=self.annoyIndex.get_nns_by_vector(sent_encode,5,include_distances=True)
        orgs=[]
        print(sent)
        for i,r in enumerate(result):
            print(str(r)+' '+str(np.cos(distance[i])))
            orgs.append(self.sents[r])
            print(self.sents[r])
        for i in self.sents:
            if(i[0]==sent):print(i)
            # print(i)

    def find_golden_org(self, content, threadhold=0.94):
        sents = list(self.splitter.split(content))
        sents=[TextProcess.delNum(TextProcess.remove_noisy(sent)).strip() for sent in sents]
        sents_encode = self.bc.encode(sents)
        result = []
        for i, sencode in enumerate(sents_encode):
            sentindex, dis = self.annoyIndex.get_nns_by_vector(sencode, 1, include_distances=True)
            print(sents[i] + str(np.cos(dis[0])))
            if (np.cos(dis[0]) > threadhold):
                result.append(
                    {'org': self.sents[sentindex[0]][1].strip(), 'subcontent': sents[i], 'score': np.cos(dis[0]),
                     'video': self.sents[sentindex[0]] if self.sents[sentindex[0]] else {}})
        return result

    def prepare(self):
        f=glob.glob('./resources/book/*.txt')
        sents=[]
        sents_=[]
        for file in f:
            with open(file, 'r',encoding='utf-8') as fin:
                lines = fin.readlines()
                bookname=lines[0].strip()
                for row in lines:
                    row=TextProcess.remove_noisy(row.strip())
                    if row==None or row=='' or len(row)<10 or row[-1] not in zhon.hanzi.punctuation:continue
                    rowsents=self.splitter.split(row)
                    for s in rowsents:
                        sents.append([s,bookname])
                        sents_.append(s)
                logging.info(bookname+str(len(sents))+'句')
        fou=open('./resources/book.bin','wb')
        pickle.dump(sents,fou)
        fou.close()
        annoyIndex=AnnoyIndex(768)
        encodes=self.bc.encode(sents_)

        for i,sent in enumerate(sents):
            encode=encodes[i]  #self.bc.encode([sent[1]])[0]
            annoyIndex.add_item(i,encode)
        annoyIndex.build(10)
        annoyIndex.save('./mod/book.mod')

    def prepare1(self):
        f = glob.glob('./resources/book/*.txt')
        sents = []
        sents_ = []
        for file in f:
            with open(file, 'r', encoding='utf-8') as fin:
                lines = fin.readlines()
                bookname = lines[0].strip()
                for row in lines:
                    row = TextProcess.remove_noisy(row.strip())
                    if row == None or row == '' or len(row) < 10 or row[-1] not in zhon.hanzi.punctuation: continue
                    rowsents = self.splitter.split(row)
                    for s in rowsents:
                        self.sents.append([s, bookname])
                        sents_.append(s)
                logging.info(bookname + str(len(sents_)) + '句')
            #改名
            p,n=os.path.splitext(file)
            os.rename(file,p +'.bak')
        fou = open('./resources/book.bin', 'wb')
        pickle.dump(self.sents, fou)
        fou.close()
        annoyIndex = AnnoyIndex(768)

        encodes = self.bc.encode(sents_)
        # count=len(self.sents)
        all=self.annoyIndex.get_n_items()
        for i, sent in enumerate(self.sents):
            # encode = encodes[i]
            if i<all:
                encode=self.annoyIndex.get_item_vector(i)
            else:
                # encode =self.bc.encode([sent[0]])[i-all]
                encode = encodes[i-all]
            annoyIndex.add_item(i, encode)
        annoyIndex.build(10)
        annoyIndex.save('./mod/book.mod')

g=BookSent()
# g.prepare1()
s='杨靖宇、赵尚志、左权、彭雪枫、佟麟阁、赵登禹、张自忠、戴安澜等一批抗日将领，八路军“狼牙山五壮士”、新四军“刘老庄连”、东北抗联八位女战士、国民党军“八百壮士”等众多英雄群体，就是中国人民不畏强暴、以身殉国的杰出代表。'
# s='青山绿水无价，清风正气可贵。墓葬乱象背后，往往有着落后思想观念的“地基”。应大力倡导文明殡葬、绿色殡葬的观念，积极移风易俗，扭转追求风水、炫富攀比等不良风气，促进形成厚养薄葬的良好风尚，引导群众保护好身边的山山水水。'
# s='绿水青山就是金山银山'
# s='一个有希望的民族不能没有英雄，一个有前途的国家不能没有先锋。'
# s='5.中华民族是崇尚英雄、成就英雄、英雄辈出的民族，和平年代同样需要英雄情怀。'
# s='“看不见的手”和“看得见的手”都要用好。'
# s='996工作制是指工作日早9点上班，晚上9点下班，中午和晚上休息1小时（或不到），总计10小时以上，并且一周工作6天的工作制度，是一种违反中华人民共和国劳动法的工作制度。'
# s='余自十月初一日起，亦照峰样，每日一念一事，皆写之于册'
# s='这些短论，鲜明提出了推进浙江经济社会科学发展的正确主张，及时回答了现实生活中人民群众最关心的一些问题。'
s='用人得当，首先要知人。'
# s='实现伟大的理想，没有平坦大道可走。'
g.findBook(s)
