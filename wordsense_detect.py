#!/usr/bin/env python3
# coding: utf-8
# File: detect.py.py
# Author: lhy<lhy_in_blcu@126.com,https://huangyong.github.io>
# Date: 18-11-17
import difflib
# import os
import pickle
import pprint
import re
# from collections import defaultdict
import time
from urllib import request
from lxml import etree
from urllib import parse
import jieba.posseg as pseg
import jieba.analyse as anse
import numpy as np
import logging
import redis
# from gensim.models import word2vec
from bert_serving.client import BertClient
from numpy.linalg import linalg

logging.basicConfig(level=logging.INFO)
logging = logging.getLogger(__name__)

class MultiSenDetect(object):
    def __init__(self):
        # cur = '/'.join(os.path.abspath(__file__).split('/')[:-1])
        # self.embedding_size = 60#300
        # self.embedding_path = os.path.join(cur,'Word60.model')# 'word_vec_300.bin')
        # self.embdding_dict = self.load_embedding(self.embedding_path)
        # 将实体相似度设置为sim_limit,将大于这个数值的两个实体认为是同一个实体
        # self.sim_limit = 0.8
        self.bc=BertClient(ip='192.168.1.101',ignore_all_checks=True)
        self.word_dict=dict()
        self.kg_dict=dict()
        #以redis代替文件
        self.redis = None
        try:
            #这是百科页面缓存
            pool = redis.ConnectionPool(host='192.168.1.101', port=6379, db=1, decode_responses=True)
            #这是向量缓存
            pool1 = redis.ConnectionPool(host='192.168.1.101', port=6379, db=2)
            #这是关键词缓存
            pool2 = redis.ConnectionPool(host='192.168.1.101', port=6379, db=3)
            self.redis = redis.Redis(connection_pool=pool)
            self.redis_1=redis.StrictRedis(connection_pool=pool1)
            self.redis_2 = redis.StrictRedis(connection_pool=pool2)
            logging.info('baidu cache in redis is connected ,count %d' % (self.redis.dbsize()))
            logging.info('word vector in redis is connected ,count %d' % (self.redis_1.dbsize()))
            logging.info('keyword in redis is connected ,count %d' % (self.redis_2.dbsize()))
            load_file = open('./mod/place_dict.bin', 'rb')
            self.place_dict = pickle.load(load_file)
            logging.info('place_dict count %d' % (len(self.aho_policical_person)))
        except:
            #如果没有redis，用文件代替
            try:
                load_file = open('./mod/baidu_cache.bin', 'rb')
                self.baidu_cache = pickle.load(load_file)
                logging.info('baidu cache count %d' % (len(self.baidu_cache)))
                load_file = open('./mod/word_dict.bin', 'rb')
                self.word_dict = pickle.load(load_file)
                logging.info('word vector dict count %d' % (len(self.word_dict)))
            except:
                self.baidu_cache = dict()
                self.word_dict = dict()



    '''请求主页面'''
    def get_html(self, url):
        if self.redis:
            if self.redis.exists(url):
                return self.redis.get(url)
            else:
                html=request.urlopen(url,timeout=600).read().decode('utf-8').replace('&nbsp;', '')
                self.redis.set(url,html)
                return html
        if self.baidu_cache:
            if self.baidu_cache.get(url):
                return self.baidu_cache.get(url)
            else:
                # request.
                content=request.urlopen(url,timeout=600).read().decode('utf-8').replace('&nbsp;', '')
                self.baidu_cache[url]=content
                return content
        # return request.urlopen(url).read().decode('utf-8').replace('&nbsp;', '')

    '''收集词的多个义项'''
    '''这里特指人物名了'''
    def collect_mutilsens(self, word):
        # if self.baidu_person.get(word):
        #     html=self.baidu_person.get(word)
        # else:
        url = "http://baike.baidu.com/item/%s?force=1" % parse.quote(word)
        html = self.get_html(url)
        # self.baidu_person[word]=html

        selector = etree.HTML(html)
        #这个判断有时候不准确
        sens = [''.join(i.split('：')[1:]) for i in selector.xpath('//li[@class="list-dot list-dot-paddingleft"]/div/a/text()')]
        sens_link = ['http://baike.baidu.com' + i for i in selector.xpath('//li[@class="list-dot list-dot-paddingleft"]/div/a/@href')]
        sens_dict = {sens[i]:sens_link[i] for i in range(len(sens)) if sens[i].strip()!=''}
        #有可能没有多概念，只有一个概念
        if len(sens_dict)==0:
            sens_dict={word:url}
        return sens_dict

    '''概念抽取'''
    def extract_concept(self, desc):
        #实际最后只取了一个，可以做成n与n相对，nr与nr相对
        desc_seg = [[i.word, i.flag] for i in pseg.cut(desc)]
        concepts_candi = [i[0] for i in desc_seg if i[1][0] in ['n','b','v','d']]
        return concepts_candi[-1]

    def extract_baidu(self, selector):
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
        # 补充元数据
        try:
            info_data['desc'] = selector.xpath('//meta[@name="description"]/@content')[0]
        except:
            info_data['desc'] =[]
        paras=[]
        para_text=''
        pattern = re.compile('“(.*?)”')
        if selector.xpath("//div[starts-with(@class,'para')]"):
            for para in selector.xpath("//div[starts-with(@class,'para')]"):
                # paras.append(para.text)
                if para.text:
                    para_text=para_text+para.text
            paras=pattern.findall(para_text)
            info_data['keywords']=self.extract_keywords(info_data['desc']+para_text)+paras# anse.extract_tags(para_text, topK=20, withWeight=False)
        else:
            info_data['keywords'] =self.extract_keywords(info_data['desc'])#[]
        #计算后面的地点、职位、最高词频等值

        # info_data['keywords']=selector.xpath('//meta[@name="keywords"]/@content')
        return info_data

    '''多义词主函数'''
    def collect_concepts(self, wd):
        #这个收集，如果我们自己建立了图谱，应该先向图谱询问，没有的情况下再向互联网查询。
        sens_dict = self.collect_mutilsens(wd)
        if not sens_dict:
            return {}
        concept_dict = {}
        concepts_dict = {}
        for sen, link in sens_dict.items():
            #     concept_dict[sen]=[link]
            #     concept = self.extract_concept(sen)
            #     if concept not in concept_dict:
            #         concept_dict[concept] = [link]
            #     else:
            #         concept_dict[concept].append(link)
            # cluster_concept_dict = self.concept_cluster(concept_dict)
            #
            # for concept, links in cluster_concept_dict.items():
            #     link = links[0]
            concept = sen
            if self.redis_2:
                if self.redis_2.exists(link):
                    concept_data=pickle.loads(self.redis_2.get(link))
                else:

                    selector = etree.HTML(self.get_html(link))
                    concept_data=self.extract_baidu(selector)
                    self.redis_2.set(link,pickle.dumps(concept_data))
                    # desc, keywords = self.extract_desc(link,wd)
                desc =concept_data['desc']
                concept_data['link']=link
                # keywords=' '.join(concept_data['keywords'])
                # context = ' '.join(desc + [' '] + concept_data['keywords'])
                context = concept_data['keywords']
                concepts_dict[concept] = context
                self.kg_dict[concept] = concept_data

        # pprint.pprint(concepts_dict)
        return concepts_dict
    def getConcept(self,concept):
        return self.kg_dict.get(concept)
    '''词义项的聚类'''
    # def concept_cluster(self, sens_dict):
    #     sens_list = []
    #     cluster_sens_dict = {}
    #     for sen1 in sens_dict:
    #         sen1_list = [sen1]
    #         for sen2 in sens_dict:
    #             if sen1 == sen2:
    #                 continue
    #             sim_score = self.similarity_cosine(self.get_wordvector(sen1), self.get_wordvector(sen2))
    #             if sim_score >= self.sim_limit:
    #                 sen1_list.append(sen2)
    #         sens_list.append(sen1_list)
    #     sens_clusters = self.entity_clusters(sens_list)
    #     for sens in sens_clusters:
    #         symbol_sen = list(sens)[0]
    #         cluster_sens_dict[symbol_sen] = sens_dict[symbol_sen]
    #
    #     return cluster_sens_dict

    '''对具有联通边的实体进行聚类'''
    # def entity_clusters(self, s):
    #     clusters = []
    #     for i in range(len(s)):
    #         cluster = s[i]
    #         for j in range(len(s)):
    #             if set(s[i]).intersection(set(s[j])) and set(s[i]).intersection(set(cluster)) and set(
    #                     s[j]).intersection(set(cluster)):
    #                 cluster += s[i]
    #                 cluster += s[j]
    #         if set(cluster) not in clusters:
    #             clusters.append(set(cluster))
    #
    #     return clusters

    '''获取概念描述信息,作为该个义项的意义描述'''
    # def extract_desc(self, link):
    #     html = self.get_html(link)
    #     selector = etree.HTML(html)
    #     #这个selector.xpath完了少东西，变成...了
    #     keywords = selector.xpath('//meta[@name="keywords"]/@content')
    #     desc = selector.xpath('//meta[@name="description"]/@content')
    #     print(desc)
    #     return desc, keywords

    '''对概念的描述信息进行关键词提取,作为整个概念的一个结构化表示'''
    def extract_keywords(self, sent):
        # keywords = [i for i in anse.extract_tags(sent, topK=20, withWeight=False, allowPOS=('n', 'v', 'ns', 'nh', 'nr', 'm', 'q', 'b', 'i', 'j')) if i !=wd]
        keywords = [i for i in anse.extract_tags(sent, topK=20, withWeight=False, allowPOS=('n', 'v', 'ns', 'nh', 'nr', 'q', 'b', 'i', 'j'))]
        return keywords

    '''加载词向量'''
    # def load_embedding(self, embedding_path):
        # embedding_dict = {}
        # count = 0
        # for line in open(embedding_path):
        #     line = line.strip().split(' ')
        #     if len(line) < 300:
        #         continue
        #     wd = line[0]
        #     vector = np.array([float(i) for i in line[1:]])
        #     embedding_dict[wd] = vector
        #     count += 1
        #     if count%10000 == 0:
        #         print(count, 'loaded')
        # print('loaded %s word embedding, finished'%count)
        # w2v=word2vec.Word2Vec.load(embedding_path)

        # return w2v#embedding_dict
        # return None
    '''基于wordvector，通过lookup table的方式找到句子的wordvector的表示'''
    '''都改用了bert的向量来表示'''
    def rep_sentencevector(self, sentence):

        return self.bc.encode([sentence])[0]
        # word_list = self.extract_keywords(sentence)
        # #用关键词叠加再取平均
        # embedding = np.zeros(self.embedding_size)
        # sent_len = 0
        # for index, wd in enumerate(word_list):
        #     if wd in self.embdding_dict:
        #         embedding += self.embdding_dict.wv.get_vector(wd) #self.embdding_dict.get(wd)
        #         sent_len += 1
        #     else:
        #         continue
        # return embedding/sent_len
    '''用BERT来取得关键词组的向量组'''
    def get_wordsvectors(self,words):
        if len(words)==0:return []
        key=''.join(words)
        #试试用mget来处理，取的时候优化，一起发送
        if self.redis_1:
            word_v_dumps = self.redis_1.mget(words)
            encodes=[]
            needencodes_word=[]
            needencodes_index=[]
            for i,dump in enumerate(word_v_dumps):
                if dump is None:
                    needencodes_index.append(i)
                    needencodes_word.append(words[i])
                else:
                    encodes.insert(i,pickle.loads(dump))
            if len(needencodes_word)>0:
                vecs=self.bc.encode(needencodes_word)
                for vec in zip(needencodes_index,vecs,needencodes_word):
                    self.redis_1.set(vec[2], pickle.dumps(vec[1]))
                    encodes.insert(vec[0],vec[1])
            return encodes
            # if self.redis_1.exists(key):
            #     return pickle.loads(self.redis_1.get(key))
            # else:
            #     vecs=self.bc.encode(words)
            #     self.redis_1.set(key, pickle.dumps(vecs))
            #     return vecs
        return self.bc.encode(words)

    '''获取单个词的词向量'''
    '''改用BERT的字向量来代词向量'''
    def get_wordvector(self, word):
        if self.redis_1:
            if self.redis_1.exists(word):
                return pickle.loads(self.redis_1.get(word))
            else:
                vec = self.bc.encode([word])[0]

                self.redis_1.set(word, pickle.dumps(vec))
                return vec
        if self.word_dict:
            if self.word_dict.get(word) is None:
                vec=self.bc.encode([word])[0]
                self.word_dict[word]=vec
            else:
                vec=self.word_dict.get(word)
            return vec#self.bc.encode([word])[0]
        # try:
        #     v=self.embdding_dict.wv.get_vector(word)
        # except:
        #     v=np.array([0]*self.embedding_size)
        # return v
        # return np.array(self.embdding_dict.get(word, [0]*self.embedding_size))
    '''两两向量之间相似度(余弦)'''
    def similarity_cosine(self, vector1, vector2):
        cos1 = np.sum(vector1 * vector2)
        cos21 = linalg.norm(vector1)
        cos22 = linalg.norm(vector2)
        # cos21 = np.sqrt(sum(vector1 ** 2))
        # cos22 = np.sqrt(sum(vector2 ** 2))
        similarity = cos1 / float(cos21 * cos22)
        if str(similarity) == 'nan':
            return 0.0
        else:
            return similarity
    '''计算两组向量之间的相关度（余弦），代替两两向量之间相似度的多重计算，速度快'''
    def similarity_cosine_matrix(self, vectors1, vectors2):
        cos1 = np.tensordot(vectors1, vectors2, axes=(1, 1))
        cos2 = np.tensordot(vectors2, vectors1, axes=(1, 1))
        # 2 - 范数：║x║2 =（│x1│2 +│x2│2 +…+│xn│2）1 / 2
        cos21 = linalg.norm(vectors1, axis=1)
        # cos21 = np.sqrt(sum(vector1**2))
        cos22 = linalg.norm(vectors2, axis=1)
        # cos22 = np.sqrt(sum(vector2**2))
        score_wds1= np.divide(cos1, (np.outer(cos21, cos22)))
        score_wds2 = np.divide(cos2, (np.outer(cos22, cos21)))
        #加权平均
        similarity1 = np.average(np.max(score_wds1, axis=1), axis=0)
        similarity2 = np.average(np.max(score_wds2, axis=1), axis=0)
        similarity=(similarity1+similarity2)/2

        if str(similarity) == 'nan':
            return 0.0
        else:
            return similarity
    #减少目标句的反复，直接用向量字典,sent1是知识数据，sent2是目标数据，vecs是目标数据的关键词向量
    def distance_words_vecs(self, sent1_keywords, sent2, vecs, word='', concept='',weightkeys=[],att=[],geo=[]):
        # TODO:这里也可以进行分析，如果有定中的词，把定中拿出来与concept进行比较
        # 简化地：如果句子中包含concept可以直接得到结论
        concept_keys = []
        if concept != '':
            concept_data=self.kg_dict.get(concept)
            #地理加权，简化版，对国际人物效果高，国内人物未处理
            if concept_data.get('国籍') and len(geo)>0:
                concept_keys.append(concept_data.get('国籍'))
            #标签加权
            # if concept_data.get('tags'):

            pattern = r',|\.|/|;|\'|`|\[|\]|<|>|\?|:|"|\{|\}|\~|!|@|#|\$|%|\^|&|\(|\)|-|=|\_|\+|，|。|、|；|‘|’|【|】|·|！| |…|（|）'
            concept_list = re.split(pattern, concept)
            for concept_sub in concept_list:
                if concept_sub.strip() == '': continue
                # score=self.similarity_cosine(self.get_wordvector(concept_sub), self.get_wordvector(word2))
                sm = difflib.SequenceMatcher(None, concept_sub, sent2)
                maxlen = sm.find_longest_match(0, len(concept_sub), 0, len(sent2)).size
                # if maxlen/ len(concept_sub) ==1:
                #     #完全一致
                #     return 1
                if maxlen / len(concept_sub) > 0.75:
                    concept_keys.append(concept_sub)#maxlen / len(concept_sub))
                    concept_keys.append(concept_sub)
                    concept_keys.append(concept_sub)

                if len(att)>0:
                    for att_ in att:
                        sm_ = difflib.SequenceMatcher(None, concept_sub, att_)
                        blocks= sm_.get_matching_blocks()
                        maxlen_=sum([b.size for b in blocks])
                                # maxlen_   (0, len(concept_sub), 0, len(att_)).size
                        if maxlen_/len(concept_sub)==1:
                            return 1
                        if maxlen / len(concept_sub) > 0.75 or maxlen / len(att_)==1:
                            concept_keys.append(att_)
                            concept_keys.append(att_)
                            concept_keys.append(att_)

                    concept_keys.append(concept_sub)
        # modi
        from scipy.spatial.distance import cosine
        # sent1 = sent1.replace('...', '').replace(word, '')
        # if sent1.strip() == '': return 0
        # wds1 = self.extract_keywords(sent1 + ' ' + concept)
        #这里能否实现：如果输入句有title，这里要加权title，如果有地名，要加权地名
        wds1 = sent1_keywords
        wds1 = wds1+concept_keys+concept_keys
        # wds2 = self.extract_keywords(sent2)
        # pprint.pprint(wds1)
        # pprint.pprint(wds2)
        score_wds1 = []
        score_wds2 = []
        sim_score = 0
        # t = time.time()
        sent1_vectors=self.get_wordsvectors(wds1)
        #补充的权重
        weightkeys_vector=[]
        for key in weightkeys:
            if key in wds1:
                i=wds1.index(key)
                weightkeys_vector.append(sent1_vectors[i])
        if len(weightkeys_vector)>0:
            sent1_vectors = np.append(sent1_vectors ,weightkeys_vector,axis=0)
            vecs =  np.append(vecs , weightkeys_vector,axis=0)
        #如果百科句的关键词过少，会导致比例提高，如果能一致呢？
        # logging.info('%s vecs length:%d,sentv length:%d' % (concept,len(vecs),len(sent1_vectors)))
        try:
            #替换算法
            sim_score=self.similarity_cosine_matrix(sent1_vectors,vecs)

            # for word1 in wds1:  # 这个模式下，在找两组词中最接近的两个词，所有的最接近值再取平均，反向再取，得到一个和第二句每个最大相似平均值。这个算法，不太好。
            #     score = max(
            #         [self.similarity_cosine(self.get_wordvector(word1),vec) for vec in vecs.values()])
            #     score_wds1.append(score)
            # for word2 in vecs:
            #     score = max(
            #         [self.similarity_cosine(vecs.get(word2), self.get_wordvector(word1)) for word1 in wds1])
            #     score_wds2.append(score)
            #这里用的是sum/len，其实还是要平滑一下，如果有max的则应该加权
            #对于keyword太少的情况，可能效果会比较差
            # 相当于定中高于向量关系，特殊情况会出现都相等的情况，再处理
            # score_wds1=score_wds1+[s for s in score_wds1 if s>=1]
            # score_wds2 = score_wds2 + [s for s in score_wds2 if s >= 1]
            # sim_score = max(sum(score_wds1) / len(wds1), sum(score_wds2) / len(vecs))
        except:
            sim_score = 0

        # logging.info(concept + 'distance_words cost:' + str(time.time() - t))
        # t = time.time()

        # if len(scores)>0:
        #     sim_score=len(scores)

        return sim_score

    # def _get_maybe_error_index(self, scores, ratio=0.6745, threshold=1.4):
    #     """
    #     取疑似错字的位置，通过平均绝对离差（MAD）
    #     :param scores: np.array
    #     :param threshold: 阈值越小，得到疑似错别字越多
    #     :return:
    #     """
    #     scores = np.array(scores)
    #     if len(scores.shape) == 1:
    #         scores = scores[:, None]
    #     median = np.median(scores, axis=0)  # get median of all scores
    #     margin_median = np.sqrt(np.sum((scores - median) ** 2, axis=-1))  # deviation from the median
    #     # 平均绝对离差值
    #     med_abs_deviation = np.median(margin_median)
    #     if med_abs_deviation == 0:
    #         return []
    #     y_score = ratio * margin_median / med_abs_deviation
    #     # 打平
    #     scores = scores.flatten()
    #     maybe_error_indices = np.where((y_score > threshold) & (scores < median))
    #     # 取全部疑似错误字的index
    #     return list(maybe_error_indices[0])

    '''基于词语相似度计算句子相似度'''
    def distance_words(self, sent1, sent2, word='', concept=''):
        #TODO:这里也可以进行分析，如果有定中的词，把定中拿出来与concept进行比较
        #简化地：如果句子中包含concept可以直接得到结论
        concept_list=[]
        if concept!='':

            pattern = r',|\.|/|;|\'|`|\[|\]|<|>|\?|:|"|\{|\}|\~|!|@|#|\$|%|\^|&|\(|\)|-|=|\_|\+|，|。|、|；|‘|’|【|】|·|！| |…|（|）'
            concept_list = re.split(pattern, concept)
            for concept_sub in concept_list:
                if concept_sub.strip()=='':continue
                # score=self.similarity_cosine(self.get_wordvector(concept_sub), self.get_wordvector(word2))
                sm = difflib.SequenceMatcher(None, concept, sent2)
                maxlen = sm.find_longest_match(0, len(concept), 0, len(sent2)).size
                if maxlen/len(concept_sub)>0.75:
                    return maxlen/len(concept_sub)
        # modi
        sent1 = sent1.replace('...', '').replace(word, '')
        if sent1.strip()=='': return 0
        wds1 = self.extract_keywords(sent1+' '+concept)
        wds2 = self.extract_keywords(sent2)
        # pprint.pprint(wds1)
        # pprint.pprint(wds2)
        score_wds1 = []
        score_wds2 = []
        sim_score = 0
        try:
            for word1 in wds1:#这个模式下，在找两组词中最接近的两个词，所有的最接近值再取平均，反向再取，得到一个和第二句每个最大相似平均值。这个算法，不太好。
                score = max([self.similarity_cosine(self.get_wordvector(word1), self.get_wordvector(word2)) for word2 in wds2])
                score_wds1.append(score)
            for word2 in wds2:
                score = max([self.similarity_cosine(self.get_wordvector(word2), self.get_wordvector(word1)) for word1 in wds1])
                score_wds2.append(score)

            sim_score = max(sum(score_wds1)/len(wds1), sum(score_wds2)/len(wds2))
        except:
            sim_score=0
        return sim_score

    '根据用户输入的句子,进行概念上的一种对齐'
    def detect_main(self, sent, word,att=[],geo=[]):
        pprint.pprint(word)
        pprint.pprint(att)
        pprint.pprint(geo)
        if att==[''] :
            att=[]
        sent = sent.replace(word, '')
        concept_dict = self.collect_concepts(word)
        # sent_vector = self.rep_sentencevector(sent)#这个句向量的得法太武断了，并不利于聚类
        concept_scores_sent = {}
        concept_scores_wds = {}

        keys = self.extract_keywords(sent)

        # keysdict=dict()
        # for key in keys:
        #     vec=self.get_wordvector(key)
        #     keysdict[key]=vec

        # for att_ in att:
        #     if att_!='':
        #         vec = self.get_wordvector(att_)
        #         keysdict[att_] = vec
        # for geo_ in geo:
        #     if geo_!='':
        #         vec = self.get_wordvector(geo_)
        #         keysdict[geo_] = vec
        # w=[]
        # if len(att) > 0:
        #     w=w+att
        # if len(geo) >0:
        #    w=w+list(geo)
        # if len(w)>0:
        #     keys=w
        keys = keys + att + list(geo)+ att + list(geo)
        pprint.pprint(keys)
        while '' in keys:
            keys.remove('')
        keys_vectors = self.get_wordsvectors(keys)

        for concept, keywords in concept_dict.items():
            if len(concept_dict) == 1:
                concept_scores_sent[concept]=1
                concept_scores_wds[concept]=1
                break
            #句向量的模式下，效果并不那么好，因为单凭一句话来聚类，还是比较偏颇的
            # try:
            #     concept_vector = self.rep_sentencevector(self.kg_dict[concept]['desc'][0])#把概念的描述句向量化，再与输入句的向量比对
            #     similarity_sent = self.similarity_cosine(sent_vector, concept_vector)
            #     concept_scores_sent[concept] = similarity_sent
            # except:
            concept_scores_sent[concept]=0
            #词向量模式下，效果还可以
            # similarity_wds = self.distance_words(desc, sent, word, concept)
            #把相同项加权做到这里了，可能反而会降速
            # keywords=keywords+list(set(keywords).intersection(set(keys)))
            #ATT分析
            geo_=[]
            for att_ in att:
                desc_seg = [[i.word, i.flag] for i in pseg.cut(att_)]
                concepts_candi = [i[0] for i in desc_seg if i[1][0] in ['ns']]
                if len(concepts_candi)>0:
                    geo_=geo_+concepts_candi
            if len(geo_)>0:
                geo=geo_
            similarity_wds = self.distance_words_vecs(keywords, sent, keys_vectors, word, concept,list(set(keywords).intersection(set(keys))),att,geo)

            concept_scores_wds[concept] = similarity_wds

        concept_scores_sent = sorted(concept_scores_sent.items(), key=lambda asd:asd[1],reverse=True)
        concept_scores_wds = sorted(concept_scores_wds.items(), key=lambda asd:asd[1],reverse=True)
        pprint.pprint(concept_scores_wds)

        # 只取了前三个，如果单从给结果的角度看，直接max给一个结果就可以
        return concept_scores_sent[:3], concept_scores_wds[:3]
    def save_cache(self):
        '''
                都处理完成后，要对现场进行保存，以提高未来的响应速度
                现在放到了变量中，未来可以由redis来保存
                '''
        # 词向量（BERT生成）
        if self.redis:
            pass
        else:
            fou = open('./mod/word_dict.bin', 'wb')
            pickle.dump(self.word_dict, fou)
            fou.close()
            # 百度人物URL内容
            fou = open('./mod/baidu_cache.bin', 'wb')
            pickle.dump(self.baidu_cache, fou)
            fou.close()
def test():
    handler = MultiSenDetect()
    # while(1):
    # sent = input('enter an sent to search:').strip()
    # wd = input('enter an word to identify:').strip()
    sent='习近平总书记强调，黄文秀同志研究生毕业后，放弃大城市的工作机会，毅然回到家乡，在脱贫攻坚第一线倾情投入、奉献自我，用美好青春诠释了共产党人的初心使命，谱写了新时代的青春之歌。'
    # sent='黄文秀现兼任教育部高等学校医学人文素质教学指导委员会委员、浙江省马克思主义理论类专业教学指导委员会副主任委员、浙江省中国特色社会主义理论体系研究中心特约研究员。'
    # sent='黄文秀1984年7月从浙江师范学院（现浙江师范大学）数学系毕业后留校工作。'
    # sent='现担任IEC/SC59L（小家电性能测试方法分技术委员会）WG6、MT3和MT4等3个标准工作组的召集人，主导制修订多项IEC标准；IEC62947（智能坐便器性能）标准起草工作组的核心成员。编撰出版多本著作，发表数十篇论文。'
    # sent='全国人大常委会副委员长王东明率调研组在我区就财政生态环保资金分配和使用情况开展专题调研。'
    # wd='王东明'
    wd='黄文秀'
    sent='杨旭严重违反党的政治纪律、廉洁纪律，构成职务违法并涉嫌受贿犯罪，且在党的十八大后不收敛、不收手，性质恶劣，情节严重，应予严肃处理。'
    sent='扶贫干部杨旭即将出版的《情满乌江》。受访者供图新华社贵阳2月23日电（记者汪军、蒋成）2019年对于扶贫干部杨旭来说，会有不少期待和憧憬：他的新书报告文学《情满乌江》年初就要出版。也是在这一年，他所在的贵州省德江县桶井土家族乡将要摘掉“贫困帽”。白天下乡，夜晚“码字”。过去两年时间，学历仅为初中二年级的杨旭，写出一本报告文学和一本新闻作品集，近43万字。用他的话来说，“43万字差不多就是桶井这个极贫乡的‘脱贫史’”。桶井是一个土家族乡，全乡23000多人中80%是土家族。这个地处武陵山集中连片特困地区深处的少数民族乡，是贵州20个极贫乡镇之一。曾经，全乡约一半的人生活处于贫困状态。“过去三四年时间，我们围绕基础设施、产业、住房等方面‘打硬仗’。”桶井乡党委书记吴飞介绍。一场接一场拼下来，扶贫干部发现，脱贫的关键还在产业，围绕花椒、脐橙、肉牛等几大主导产业，桶井未来发展可期。正如杨旭的《情满乌江》所记录：新建“组组通”公路62条，长达167.69公里；调减玉米等低收入作物，栽种花椒1.5万亩；打造医共体，群众看病难、看病贵的问题得到解决；新建中小学和幼儿园，配套设施齐全……扶贫干部杨旭正在写作。受访者供图“这本书不是简单把材料串联起来，而是通过真实的故事，把扶贫干部埋头苦干的精气神写出来。”杨旭说，桶井土家族乡摘掉“贫困帽”后，所有在这片土地上付出过汗水的扶贫干部，再来看他写的文字时，一定会有共鸣。2016年，负责党建工作的杨旭对新闻写作产生兴趣。“虽然只读到初二，但文字功底好，现在乡里不少材料都是他操刀的。”桶井土家族乡宣传委员罗君说。同扶贫干部进村入户，杨旭注重发现桶井这片土地上那些为大家所称赞的人和事。回到办公室，夜深人静时，思绪随着键盘翻飞，用文字勾勒出干部群众摆脱贫困的情景。其中有基层干部扎根山乡谋脱贫之策的感人故事，还有乡镇在脱贫攻坚中的创新经验。他用更加丰富的细节和更细腻的笔触，将饱满的极贫乡“脱贫史”，用近25万字装进《情满乌江》一书中。“这些文字是桶井土家族乡历史的一部分，也是我人生的一部分。”杨旭说。'
    #[('南阳师范学院老师', 0.5725757241076156), ('四川省成都市兴网传媒公司副总经理', 0.5699658518479743), ('英特尔公司全球副总裁兼中国区总裁', 0.5665771964583592)]
    #结果不准，但可判断不是违纪官员
    sent='更为可怕的是，其他一些总代理商从杨旭手中得到赌博网站账号密码后，又自行发展下线，吸收赌徒下注。'
    # sent='比赛第27分钟，杨旭在左路拿球准备内切，而防守他的则是鲁能后卫戴琳，两人在进行一个对脚之后，杨旭完全过掉了戴琳。'
    #[('中国足球运动员', 0.5913730414196107), ('南阳师范学院老师', 0.5880194427854896), ('原辽宁省国土资源厅巡视员', 0.5839426325332834)]
    wd='杨旭'

    sent='中共十九届中央政治局常委，国务院总理、党组书记李克强发表讲话'
    wd='李克强'

    sent_embedding_res, wds_embedding_res = handler.detect_main(sent, wd)
    print(sent_embedding_res)
    print(wds_embedding_res)
    # handler.save_cache()
    #要两个结果一致才好，但句子级的仅是语义相似，而非相关。
    #而所有结果都是猜测的，并不如一些直观的定中关系直接决定的好，例如：国务院总理李克强。这部分还要在这之前先处理。

def mergeBaiduCache():
    baidu_cache=dict()
    for i in range(10):
        print(i)
        load_file = open('./mod/baidu_cache'+str(i)+'.bin', 'rb')
        baidu_cache_ = pickle.load(load_file)
        baidu_cache.update(baidu_cache_)
    pprint.pprint(len(baidu_cache))
    out = open('./mod/baidu_cache.bin', 'wb')
    out.write(pickle.dumps(baidu_cache))
    out.close()

def vectors_max_cosin_test():
    m = MultiSenDetect()
    w1 = ['中共', '党委', '书记']
    w2 = ['中共', '特别', '娱乐']
    m1 = m.bc.encode(['中共', '党委', '书记'])
    m2 = m.bc.encode(['中共', '特别', '娱乐'])
    m3 = m.bc.encode(['娱乐', '明星', '电视'])
    print(m.similarity_cosine_matrix(m1, m2))
    # print(m.similarity_cosine_matrix(m2, m1))
    print(m.similarity_cosine_matrix(m1, m3))

    score_wds1 = []
    score_wds2 = []
    for word1 in w1:  # 这个模式下，在找两组词中最接近的两个词，所有的最接近值再取平均，反向再取，得到一个和第二句每个最大相似平均值。这个算法，不太好。
        score = max([m.similarity_cosine(m.get_wordvector(word1), m.get_wordvector(word2)) for word2 in w2])
        score_wds1.append(score)
    print(sum(score_wds1) / len(m1))

if __name__ == '__main__':
    test()
    # mergeBaiduCache()
    # test()
    # vectors_max_cosin_test()
    # m = MultiSenDetect()
    # print(m.get_wordsvectors(['首领','大家']))
