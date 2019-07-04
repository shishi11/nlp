# -*-coding:utf-8-*-
import glob
import logging
import pickle
import pyltp

from openpyxl import load_workbook
from bert_serving.client import BertClient
from annoy import AnnoyIndex
import numpy as np

from textProcess import TextProcess

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)

class GoldenSent():
    def __init__(self):
        self.bc=BertClient(ip='192.168.1.101',ignore_all_checks=True)
        self.splitter = pyltp.SentenceSplitter()
        self.annoyIndex=AnnoyIndex(768)
        self.annoyIndex.load('./mod/golden_wwm.mod')
        load_file=open('./resources/golden1.bin','rb')
        self.sents=pickle.load(load_file)
        logger.info('%d golden sentances loaded',len(self.sents))


    def findGolden(self,sent):
        sent_encode=self.bc.encode([sent])[0]
        result,distance=self.annoyIndex.get_nns_by_vector(sent_encode,5,include_distances=True)
        orgs=[]
        print(sent)
        for i,r in enumerate(result):
            print(str(r)+' '+str(np.cos(distance[i])))
            orgs.append(self.sents[r])
            print(self.sents[r])

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
        f=glob.glob('./resources/golden/*.xlsx')
        sents=[]
        for file in f:
            wb = load_workbook(file)
            a_sheet = wb.get_sheet_by_name('Sheet1')
            for row in a_sheet.rows:
                if row[0].value==None or row[0].value=='日期':continue
                id=row[0].value
                content=row[1].value
                desc=row[2].value
                sents.append([id,content,desc])
        logging.info(str(len(sents))+'句')
        fou=open('./resources/golden.bin','wb')
        pickle.dump(sents,fou)
        fou.close()
        annoyIndex=AnnoyIndex(768)
        for i,sent in enumerate(sents):
            encode=self.bc.encode([sent[1]])[0]
            annoyIndex.add_item(i,encode)
        annoyIndex.build(10)
        annoyIndex.save('./mod/golden.mod')

    def prepare1(self):

        allsents=[]
        for sent in self.sents:
            sents = list(self.splitter.split(sent[1]))
            # sents_encode = self.bc.encode(sents)
            for subsent in sents:
                subsent = subsent.strip()
                if subsent!=None and len(subsent)>4:
                    allsents.append([sent[0],subsent,sent[2],sent[1]])
        logging.info(str(len(allsents))+'句')
        fou=open('./resources/golden1.bin','wb')
        pickle.dump(allsents,fou)
        fou.close()
        annoyIndex = AnnoyIndex(768)
        for i,sent in enumerate(allsents):

            logging.info(str(i)+sent[1])
            if(sent[1]==''):
                print('')
            encode = self.bc.encode([sent[1]])[0]
            annoyIndex.add_item(i, encode)
        annoyIndex.build(10)
        annoyIndex.save('./mod/golden_wwm.mod')

g=GoldenSent()
# g.prepare1()
# s='杨靖宇、赵尚志、左权、彭雪枫、佟麟阁、赵登禹、张自忠、戴安澜等一批抗日将领，八路军“狼牙山五壮士”、新四军“刘老庄连”、东北抗联八位女战士、国民党军“八百壮士”等众多英雄群体，就是中国人民不畏强暴、以身殉国的杰出代表。'
# s='青山绿水无价，清风正气可贵。墓葬乱象背后，往往有着落后思想观念的“地基”。应大力倡导文明殡葬、绿色殡葬的观念，积极移风易俗，扭转追求风水、炫富攀比等不良风气，促进形成厚养薄葬的良好风尚，引导群众保护好身边的山山水水。'
# s='绿水青山就是金山银山'
# s='一个有希望的民族不能没有英雄，一个有前途的国家不能没有先锋。'
# s='5.中华民族是崇尚英雄、成就英雄、英雄辈出的民族，和平年代同样需要英雄情怀。'
# s='“看不见的手”和“看得见的手”都要用好。'
# s='青年要为世界进文明，为人类造幸福，以青春之我，创建青春之家庭，青春之国家，青春之民族，青春之人类，青春之地球，青春之宇宙，资以乐其无涯之生。'
s='习近平指出，要紧紧扭住战争和作战问题推进军事理论创新，构建具有我军特色、符合现代战争规律的先进作战理论体系，不断开辟当代中国马克思主义军事理论发展新境界。要打通从实践到理论、再从理论到实践的闭环回路，让军事理论研究植根实践沃土、接受实践检验，实现理论和实践良性互动。'
# s='欲知平直，则必准绳；欲知方圆，则必规矩。'
# s='一带一路'
g.findGolden(s)
