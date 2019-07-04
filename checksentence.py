import difflib

import gensim
import re

from bert_serving.client import BertClient
from annoy import AnnoyIndex

from textProcess import TextProcess


class CheckSent():
    w2v_model_path='./mod/Word60.model'
    def __init__(self):
        self.bc=BertClient(ip='192.168.1.101',ignore_all_checks=True)
        # self.w2v=gensim.models.word2vec.Word2Vec.load(self.w2v_model_path)


    def test(self):
        orgs=['对会议议程而言，一天的时间显得紧张了些，但我们直奔主题，谈得务实充分，既有深度，也有广度，收获了丰富成果。','具体而言，我们在以下几个方面形成了广泛共识。']
        trans=[[0,'先生们，女士们，朋友们。'],[1,'对于会议异常而言，一天的时间，显得紧张了些。'],[2,'我们直奔主题。'],[3,'谭得物质充分。'],[4,'有深度，也有广度，收获了丰富成果。'],[5,'具体而言，我们在以下。'],[6,'几个方面？行成了广泛共识。']]
        self.check(orgs,trans)
        self.wcheck(orgs,trans)
    def check(self,orgs,trans):

        annoyIndex = AnnoyIndex(768)
        #原始的长句切成短句
        sents=[]
        i=0
        #先把原句拆短句后放到索引中
        for org in orgs:
            org_shorts=re.split('。|，|！|？|;',org.strip())
            org_shorts=[s for s in org_shorts if s!='']
            vecs = self.bc.encode(org_shorts)
            sent=[]
            for n,org_short in enumerate(org_shorts):
                annoyIndex.add_item(i, vecs[n])

                sent.append(i)
                i += 1
            sents.append(sent)
        annoyIndex.build(1)
        print('原始句：')
        print(sents)

        #译文拆成短句
        tran_sents=[]
        # 译文位置
        trans_ids=[]
        i = 0
        for tran in trans:
            sent=tran[1].strip()
            tran_shorts=re.split('。|，|！|？|;',sent)
            tran_shorts=[t for t in tran_shorts if t!='']
            sent = []
            for num, tran_short in enumerate(tran_shorts):
                tran_sents.append(tran_short)
                sent.append(i)
                i+=1
            trans_ids.append(sent)
        print('译文')
        print(trans_ids)

        #计算译文与原文的关系
        result = []
        #原文短句位置
        current = 0
        #初始短句
        current_short = ''
        for num,tran_short in enumerate(tran_sents):
            #译文会比原文短，要计算本句和本句与下一句合成，如果合成句更接近原文，则跳过本次计算，下次
            #以合成句为初始值，再合成下一句。
            if(current_short==''):
                current_short+=tran_short
            vec=self.bc.encode([current_short])[0]
            if num<len(tran_sents)-1:
                concat=current_short+tran_sents[num+1]
            # 利用向量计算最接近原文短句的译文短句或译文合成句（也可以有其它方法计算，本质是句子相似度计算）
            vec_ = self.bc.encode([concat])[0]
            index,dis=annoyIndex.get_nns_by_vector(vec,1, include_distances=True)#这就是最接近的了
            index_,dis_=annoyIndex.get_nns_by_vector(vec_,1, include_distances=True)

            if dis[0]<0.01:
                current_short = ''
                current=index[0]
                result.append([current, num, dis[0]])
                current += 1
                continue

            if dis_[0]<dis[0] and index==index_  and index[0]-current<3:
                current_short=concat
                continue
            elif index[0]-current>=3:
                current_short=''
                continue
            #index[0]是计算得到的最相似的原始短句位置
            if(index[0]==current and current==0):
                current_short=''
                result.append([current, num,dis[0]])
                current+=1
                continue
            elif(index[0]-current<3 and current!=0):
                #也会出现原文2句对应译文的3句的情况，需要跳过原文位置。
                current=index[0]
            # elif(index[0]-current>=3):
                # current_short=''
                # continue
            #结果中距离接近0的，基本就是原句，是对应关系的检查点
            if len(result)>0:
                result.append([current, num,dis[0]])
                current+=1
            current_short = ''
        print(result)

        #只计算原始句子的起始位置和结束位置，中间可以不算
        tran_result=[]
        for sent in sents:#这是原始句子
            b=sent[0]
            e=sent[-1]
            t=[]
            for s in result:
                if s[0]==b:
                    t.append(s[1])
                if s[0]==e:
                    t.append(s[1])
            #结束位置不清晰的，由下一句的起始位置倒推计算
            if len(tran_result)>0 and len(tran_result[-1])==1:
                tran_result[-1].append(t[0]-1)
            tran_result.append(t)
        #原文对应的译文短句分布
        print(tran_result)
        for i,tr in enumerate(tran_result):
            print(orgs[i])
            for n,id in enumerate(trans_ids):
                if id[0]>=tr[0] and id[-1]<=tr[1]:
                    #原文对应的译文长句分布
                    print(trans[n])
    def wcheck(self,orgs,trans):
        #先加载Wv
        #分词，
        #计算相似
        sents=[]
        i=0
        org_all=''
        for org in orgs:
            org_all+=org
        tran_all=''.join([tran[1] for tran in trans])
        print(org_all,tran_all)
        diff=difflib.Differ()
        print('\n'.join(list(diff.compare(org_all,tran_all))))
        s=difflib.SequenceMatcher(None,org_all,tran_all)
        block=s.get_matching_blocks()
        print(block)
        op=s.get_opcodes()
        print(op)
        #这只是没有分词情况下的，如果是纠错，对于非equal之外的部分，都要进行分词的演练
        #情况要分为。多字，少字，错字，换词等多种情况
        rs=[o for o in op if o[0]=='replace' and o[2]-o[1]>1 and o[4]-o[3]>1]
        for r in rs:
            print(org_all[r[1]:r[2]],'-->',tran_all[r[3]:r[4]])

            # org_shorts = re.split('。|，|！|？|;', org.strip())
            # org_shorts = [s for s in org_shorts if s != '']
            # sent = []
            # for n, org_short in enumerate(org_shorts):
            #     doc=list(TextProcess.cut(org_short))
                # dis=self.w2v.wmdistance(doc,doc)
                # print(dis)


check=CheckSent()
check.test()