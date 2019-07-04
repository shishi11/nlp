import glob
import logging
import pickle
import pyltp
import time

import pymysql
from bert_serving.client import BertClient
import numpy as np
import json
from annoy import AnnoyIndex


# from service.client import BertClient
from gensim import similarities

from scipy.linalg import norm

class sentenceParser():
    def __init__(self):

        self.bc = BertClient(ip='192.168.1.103')
        self.splitter = pyltp.SentenceSplitter()
        # fin = open('./resources/ninteenth_sents.txt', 'r', encoding='UTF-8')
        #
        # self.lines = fin.readlines()
        # fin.close()

        self.annoyIndex=AnnoyIndex(768)
        # self.annoyIndex.load('./mod/annoy_19th.model')
        self.annoyIndex.load('./mod/annoy_19th_vedio.mod')
        load_file=open('./resources/19th_vedio.bin','rb')
        self.sents=pickle.load(load_file)
        self.lines=[sent['articleContent'] for sent in self.sents]

    def find_19th_org(self,content,threadhold=0.9):
        sents = list(self.splitter.split(content))
        sents_encode=self.bc.encode(sents)
        result=[]
        for i,sencode in enumerate(sents_encode):
            sentindex,dis=self.annoyIndex.get_nns_by_vector(sencode,1,include_distances=True)
            print(sents[i]+str(np.cos(dis[0])))
            if(np.cos(dis[0])>threadhold):
                result.append({'org':self.lines[sentindex[0]].strip(),'subcontent':sents[i],'score':np.cos(dis[0]),'video':self.sents[sentindex[0]] if self.sents[sentindex[0]] else {} })
        return result


    def connect_wxremit_db(self):
        return pymysql.connect(host='127.0.0.1',
                               port=3306,
                               user='root',
                               password='',
                               database='xinhua',
                               charset='utf8')


    def query_country_name(self, cc2):
        sql_str = ("SELECT distinct(FILE_UUID),txt"
                   + " FROM e20190313"
                   + " WHERE txt like '%s' group by FILE_UUID,txt limit 100" % cc2)
        logging.info(sql_str)

        con = self.connect_wxremit_db()
        cur = con.cursor()
        cur.execute(sql_str)
        rows = cur.fetchall()
        cur.close()
        con.close()

        # assert len(rows) == 1, 'Fatal error: country_code does not exists!'
        return rows
    def prepare_vedio(self):
        f = glob.glob('./resources/19/*.txt')
        sents=[]
        for file in f:
            print(file)
            with open(file,'r') as fin:
                lines=fin.readlines()
                for line in lines:
                    line=line.replace('\'','"')
                    js = json.loads(line)
                    # jsonp = jsonpath.jsonpath(js, "$..news.*")
                    sents.append(js)
        #应该做成KEY vALUE
        self.sents=sents#[{str(i):sent} for i,sent in enumerate(sents)]
        annoyIndex = AnnoyIndex(768)
        for i,sent in enumerate(sents):
            encode = self.bc.encode([sent['articleContent']])[0]
            # sent_id=int(sent['sentenceId'][12:])
            annoyIndex.add_item(i,encode)
        annoyIndex.build(10)
        annoyIndex.save('./mod/annoy_19th_vedio.mod')
        fou=open('./resources/19th_vedio.bin','wb')
        pickle.dump(self.sents,fou)
        fou.close()
        # fou = np.array(self.sents, dtype=np.float32)
        # fou.tofile("./resources/19th_vedio.bin")


    def prepare(self):
        fin=open('./resources/ninteenth','r',encoding='UTF-8')
        sentfile=open('./resources/ninteenth_sents.txt','w',encoding='UTF-8')

        '''
        AnnoyIndex(f, metric='angular') returns a new index that’s read-write and stores vector of f dimensions. Metric can be "angular", "euclidean", "manhattan", "hamming", or "dot".
        '''
        annoyIndex = AnnoyIndex(768)
        i=0
        sents_encode=[]
        lines=fin.readlines()
        for line in lines:
            line=line.strip()
            if line!='':
                sents=list(self.splitter.split(line))
                encodes=self.bc.encode(sents)

                for sent in zip(sents,encodes):
                    sents_encode.append(sent[1])
                    sentfile.write(sent[0]+'\n')
                    annoyIndex.add_item(i, sent[1])
                    i+=1
        #             # sents_encode.append({'content':sent[0],'encode':sent[1]})
        annoyIndex.build(100)
        annoyIndex.save('./mod/annoy_19th.model')

        fin.close()
        sentfile.close()

        fou=np.array(sents_encode,dtype=np.float32)
        fou.tofile("./resources/19.bin")
        # fou=open('./resources/ninteenth_encode.txt','w',encoding='UTF-8')
        # for index,sent in enumerate(sents_encode):
        #     fou.write(str(index)+'\t'+sent['content']+'\t'+str(sent['encode'])+'\n')
        # fou.close()
        # import numpy as np
        # dis1 = np.dot(a[1], b[1]) / (norm(a[1]) * norm(b[1]))
        # dis2 = np.dot(b[0], c[0]) / (norm(b[0]) * norm(c[0]))
        # print(dis1, dis2)


    def proccess_main(self):
        # self.encodes=np.fromfile('./resources/19.bin',dtype=np.float32)
        # print(encodes)
        content='习近平总书记在党的十九大报告中指出，中国秉持共商共建共享的全球治理观，积极参与全球治理体系改革和建设，不断贡献中国智慧和力量。'
        content='世界正处于大发展大变革大调整时期，和平与发展仍然是时代主题'
        content='我们愿同意方共建“一带一路”，发挥两国“一带一路”合作的历史、文化、区位等优势，把“一带一路”互联互通建设同意大利“北方港口建设计划”、“投资意大利计划”等对接，在海上、陆地、航空、航天、文化等多个维度打造新时期的“一带一路”'
        # content='同志们：
        content='党的十九大报告指出：“我国社会主要矛盾已经转化为人民日益增长的美好生活需要和不平衡不充分的发展之间的矛盾”。从群众的需求上看，美好生活日益多样化，不仅包括物质方面的需求，还包括非物质需求。2017年12月份，厦门开始全力打造“五安工程”，从群众最关心、最直接的“家安、路安、食安、业安、心安”等平安需求着力，为打造最具安全感城市加油助力。'
        # self.getSimilray(content)
        # print('*'*15+content)
        # self.getSimilray2(content)
        print(self.find_19th_org(content))


    def getSimilray2(self,content):
        current = self.bc.encode([content])
        # annoyIndex=AnnoyIndex(768)
        # for i,encode in enumerate(self.encodes.reshape(-1, 768)):
        #     annoyIndex.add_item(i,encode)
        # annoyIndex.build(100)
        result,distance=self.annoyIndex.get_nns_by_vector(current[0],5,include_distances=True)
        orgs=[]
        print(content)
        for i,r in enumerate(result):
            print(str(r)+' '+str(np.cos(distance[i])))
            # print(self.lines[r])
            # orgs.append(self.lines[r])
            orgs.append(self.sents[r])
            print(self.sents[r])

        distance=np.array(np.cos(distance)).tolist()
        return orgs,distance

    def getSimilray1(self,content):
        # None
        # current = self.bc.encode([content])
        # index=similarities.MatrixSimilarity(self.encodes.reshape(-1, 768),num_features=768,chunksize=768)
        # sim=index[current[0]]
        # sim=sorted(enumerate(sim),key=lambda item:item[1],reverse=True)
        # for i in sim[:-5]:
        #     print(i)
        #     print(self.lines[i[0]])
        current = self.bc.encode([content])
        score=np.sum(current[0]*self.encodes.reshape(-1, 768),axis=1)/np.linalg.norm(self.encodes.reshape(-1, 768),axis=1)
        topk=np.argsort(score)[::-1][:5]
        print(topk)



    def getSimilray(self,content):
        current=self.bc.encode([content])
        dtype = [('index',np.int), ('score',np.float32)]

        all=[]

        for index,encode in enumerate(self.encodes.reshape(-1,768)):
            distance=np.dot(current[0],encode)/(norm(current[0])*norm(encode))
            # if(distance>top[1]):
            all.append([index,distance])
        # all = np.array(all, dtype=dtype)
        # top=  np.sort(all,order='score')
        top=sorted(all,key=lambda elem:elem[1],reverse=True)

        for i in top[:5]:
            print(i)
            print(self.lines[i[0]])

    def test(self):
        # feat=np.random.random((100000,4096))
        # annoyIndex = AnnoyIndex(4096)
        # annoyIndex.on_disk_build('a')
        # for i,v in enumerate(feat):
        #     annoyIndex.add_item(i,v)
        # for i,v in enumerate(feat):
        #     annoyIndex.add_item(i,v)
        t=time.time()
        #
        # annoyIndex.build(100)
        # print(time.time()-t)
        annoyIndex = AnnoyIndex(4096)
        annoyIndex.load('a')
        print(annoyIndex.get_nns_by_item(0,5))
        print(time.time() - t)

    def test1(self):
        rows=self.query_country_name('%')
        annoyIndex = AnnoyIndex(768)
        # for i,row in enumerate(rows):
        #     encode=self.bc.encode([row[1]])
        #     annoyIndex.add_item(i,encode[0])
        # annoyIndex.build(10)
        # annoyIndex.save('articles')
        annoyIndex.load('articles')
        result,index=annoyIndex.get_nns_by_item(10,5,include_distances=True)
        print(rows[10])
        print(np.cos(index))
        for i in result:

            print(rows[i])

sentP=sentenceParser()
# sentP.prepare()
# sentP.prepare_vedio()

sentP.proccess_main()
# sentP.test1()
