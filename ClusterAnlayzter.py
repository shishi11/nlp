# -*- coding:utf-8 -*-
'''
迭代二分聚类
根据hanlp1.X中的ClusterAnalzyer进行改写，在以往的测试中，发现其结果还算可以
但原来的代码中把向量化封装到代码中，用的是类似CountVectorizer的方式。且java显然没有python更适合矩阵和向量的操作
'''

import json
import logging
import math
import random
from enum import Enum
from queue import PriorityQueue

import matplotlib.pyplot as plt
import numpy as np
from bert_serving.client import BertClient
from gensim import models
from pyhanlp import *
from sklearn.decomposition import PCA

logging.basicConfig(level=logging.INFO)
logging = logging.getLogger(__name__)

from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer


class ClusterAnalyzer():
    # refine的默认迭代次数，一般情况下达不到
    NUM_REFINE_LOOP = 30

    # 测试方式
    class MODELS(Enum):
        COUNTVECTORIZER = 'CountVectorizer'
        TFIDFVECTORIZER = 'TfidfVectorizer'
        TFIDFVECTORIZER_PCA = 'TfidfVectorizer_PCA'
        WORD2VEC = 'Word2Vec'
        WORD2VECSELF = 'Word2VecSelf'
        BERT = 'Bert'
        BERT_PCA = 'Bert_PCA'

    def __init__(self, model=MODELS.COUNTVECTORIZER, model_path='./mod/fasttext'):
        self.document_ = []
        # 判断准则，用于cluster的比较
        self.sectioned_gain_ = 0.0
        #使用的模型
        if isinstance(model, self.MODELS):
            self.model = model
        else:
            # logging.error('model错误，需要使用ClusterAnlayzer.MODELS中的模型')
            raise Exception('model错误，需要使用ClusterAnlayzer.MODELS中的模型')

        # 原始分行数据，空格分词，BERT则是整句
        self.corpus = []
        # 原始分行数据分词
        self.listcorpus = []
        # 原始数据索引，放在外面，方便后续由应用处理
        self.corpu_indexes = []
        # 分词工具，但看起来效果一般，可改用hanlp2.0或是ltp的
        self.segment = HanLP.newSegment().enableNameRecognize(True)
        # 停用词表，这个也可以改造
        self.CoreStopWordDictionary = JClass('com.hankcs.hanlp.dictionary.stopword.CoreStopWordDictionary')
        self.model_path = model_path

    '''
    初始化word2vec模型
    '''
    def init_word2vec_model(self):

        # 这个300维的模型，由hanlp2.X的模型下载而来，重新处理成bainary=True，小而快
        # 原来的模型为ctb.fasttext.300.txt，binary=False,no_header=True
        # word2vec_model=models.KeyedVectors.load_word2vec_format('./model/sgns.renmin.bigram-char')
        word2vec_model = models.KeyedVectors.load_word2vec_format(self.model_path, binary=True)
        logging.info('加载word2vec完成，测试：')
        logging.info('中国')
        logging.info(self.word2vec_model['中国'])
        return word2vec_model

    # 留一个口子从外部加载向量
    def addDocument(self, index, vector: []):
        self.document_.append((index, vector))

    '''
    按行加载原始数据，转成模型可处理的语料
    BERT不需要分词，整文本放入
    '''

    def addDocument(self, index, document: str):
        self.corpu_indexes.append(index)
        if self.model == self.MODELS.BERT or self.model == self.MODELS.BERT_PCA:
            self.corpus.append(document)
        else:
            # 先分词处理变成空格分隔字串
            corpus_, listcorpus_ = self.preprocess(document)
            self.corpus.append(corpus_)
            self.listcorpus.append(listcorpus_)

    '''
    将语料转成向量，根据不同的模型，被转成不同的向量
    '''
    def corpu2vector(self):
        if self.model == self.MODELS.COUNTVECTORIZER:
            vectorizer = CountVectorizer(min_df=1, max_df=1.0, token_pattern='\\b\\w+\\b')
            count_train = vectorizer.fit_transform(self.corpus)
            vectors = count_train.toarray().tolist()

        if self.model == self.MODELS.TFIDFVECTORIZER:
            transformer = TfidfVectorizer()
            tfidf = transformer.fit_transform(self.corpus)
            vectors = tfidf.toarray().tolist()

        if self.model == self.MODELS.TFIDFVECTORIZER_PCA:
            transformer = TfidfVectorizer()
            tfidf = transformer.fit_transform(self.corpus)
            pca = PCA(n_components=10)
            vectors = pca.fit_transform(tfidf.toarray())

        if self.model == self.MODELS.WORD2VEC:
            vectors = []
            word2vec_model = self.init_word2vec_model()
            for wordList in self.listcorpus:
                cv = np.sum(word2vec_model[wordList], axis=0)
                nrm = np.linalg.norm(cv)
                vectors.append(cv / nrm)

        if self.model == self.MODELS.BERT or self.model == self.MODELS.BERT_PCA:
            #由bert as service服务来处理
            bc = BertClient()
            cv = bc.encode(self.corpus)
            nrm = np.linalg.norm(cv)
            vectors = cv / nrm
            if self.model == self.MODELS.BERT_PCA:
                pca = PCA(n_components=10)
                vectors = pca.fit_transform(vectors)
        logging.info('corpu2vector use %s transformed %d rows', self.model, len(self.corpu_indexes))
        # logging.info(list(zip(self.corpu_indexes, self.listcorpus)))
        self.document_ = list(zip(self.corpu_indexes, vectors))

    '''
    预处理文本，对于word2vec要去除不在单词表中的词
    对于word2vec，处理时就保证单词在词表中
    '''
    def preprocess(self, document):
        termList = self.segment.seg(document)
        wordList = []
        if self.model == self.MODELS.WORD2VEC:
            for term in termList:
                if self.word2vec_model.has_index_for(term.word):
                    wordList.append(term.word)
        else:
            for term in termList:
                if not (self.CoreStopWordDictionary.contains(term.word) or term.nature.startsWith("w")):
                    wordList.append(term.word)
        return ' '.join(wordList), wordList

    '''
    直接将向量矩阵加载进来，方便在外部进行向量化
    '''
    def addDataSet(self, dataSet):
        for index in range(dataSet.shape[0]):
            self.document_.append((index, dataSet[index, :]))

    # 计算欧式距离
    def euclDistance(self, vector1, vector2):
        return np.sqrt(sum(pow(vector2 - vector1, 2)))  # pow()是自带函数

    '''
    基于余弦相似度计算句子之间的相似度，句子向量等于字符向量求平均
    如果基于不同特征拼接情况，则inner的意义更好，hanlp原始用的inner
    '''
    def similarity_cosine(self, vector1, vector2):
        # cos1 = np.sum(vector1*vector2)
        # cos21 = np.sqrt(sum(vector1**2))
        # cos22 = np.sqrt(sum(vector2**2))
        # similarity = cos1/float(cos21*cos22)
        similarity = np.inner(vector1, vector2)
        return similarity

    '''
    /**
     * repeated bisection 聚类   改造自hanlp
     *  迭代二分
     * @param nclusters  簇的数量
     * @param limit_eval 准则函数增幅阈值
     * @return 指定数量的簇（Set）构成的集合
     */
    '''
    def repeatedBisection(self, nclusters, limit_eval):
        numSamples = len(self.document_)
        if nclusters > numSamples:
            logging.error("传入聚类数目%d大于文档数量%d，已纠正为文档数量\n", nclusters, numSamples)
            nclusters = numSamples

        cluster = Cluster()
        clusters_ = []
        for document in self.document_:
            cluster.add_document(document)
        cluster.section(2)
        self.refine_clusters(cluster.sectioned_clusters())

        cluster.set_sectioned_gain()  # 后面比较时用
        # cluster.composite_vector().clear();
        cluster.composite_ = []
        '''
        这个优先级的意义是下次找出section_gain比较大的那一簇进行分割
        由Cluster的内部方法 __it__进行处理
        '''
        que = PriorityQueue()
        que.put(cluster)
        while (que.qsize() != 0):
            if (nclusters > 0 and que.qsize() >= nclusters):
                break
            cluster = que.get()
            if len(cluster.sectioned_clusters()) < 1:
                que.put(cluster)
                break
            if (limit_eval > 0 and cluster.sectioned_gain() < limit_eval):
                que.put(cluster)
                break

            sectioned = cluster.sectioned_clusters()
            for c in sectioned:
                if c.size() >= 2:
                    c.section(2)  # 进行了之后，就是section_clusters了
                    self.refine_clusters(c.sectioned_clusters())
                    c.set_sectioned_gain()
                    if (c.sectioned_gain() < limit_eval):
                        for sub in c.sectioned_clusters():
                            sub.clear()
                    c.composite_vector_ = []
                que.put(c)

        while (que.qsize() != 0):
            c_ = que.get()
            clusters_.append(c_)
        return self.toResult(clusters_)

    '''
    结果集为各簇的数据索引
    '''
    def toResult(self,clusters_):
        clusters_indexes=[]
        for c in clusters_:
            s_indexes=[]
            for d in c.documents_:
                s_indexes.append(d[0])
            clusters_indexes.append(s_indexes)
        return  clusters_indexes

    '''
    根据k-means算法迭代优化聚类
    clusters是初始化质心后及数据的kmeans簇
    返加准则函数值
    '''
    def refine_clusters(self, clusters):
        norms = []
        for cluster_ in clusters:
            '''
            math.sqrt( np.sum(np.power(cluster_.composite_vector(),2))))
            明显python的矩阵计算比java方便很多
            '''
            norms.append(np.linalg.norm(
                cluster_.composite_vector()))

        eval_cluster = 0.0
        for loop_count in range(self.NUM_REFINE_LOOP):
            '''
            将数据打乱
            '''
            items = []
            for i in range(len(clusters)):
                for j in range(len(clusters[i].documents())):
                    items.append((i, clusters[i].documents()[j]))
            np.random.shuffle(items)

            changed = False
            for item in items:
                cluster_id = item[0]
                cluster = clusters[cluster_id]
                doc = item[1]  # cluster.documents()[item_id]
                value_base = self.refined_vector_value(cluster.composite_vector(), doc[1], -1)
                norm_base_moved = math.pow(norms[cluster_id], 2) + value_base
                norm_base_moved = math.sqrt(norm_base_moved) if norm_base_moved > 0 else 0.0

                eval_max = -1.0
                norm_max = 0.0
                max_index = 0
                for j, other in enumerate(clusters):
                    if (cluster_id == j):
                        continue
                    value_target = self.refined_vector_value(other.composite_vector(), doc[1], 1)
                    norm_target_moved = math.pow(norms[j], 2) + value_target
                    norm_target_moved = math.sqrt(norm_target_moved) if norm_target_moved > 0 else 0.0
                    eval_moved = norm_base_moved + norm_target_moved - norms[cluster_id] - norms[j]
                    if (eval_max < eval_moved):
                        eval_max = eval_moved
                        norm_max = norm_target_moved
                        max_index = j
                if (eval_max > 0):
                    eval_cluster += eval_max
                    clusters[max_index].add_document(doc)
                    clusters[cluster_id].remove_document(doc)
                    norms[cluster_id] = norm_base_moved
                    norms[max_index] = norm_max
                    changed = True

            if (not changed):
                break
            for cluster in clusters:
                cluster.refresh()
        return eval_cluster, clusters, norms

    '''
    # c^2 - 2c(a + c) + d^2 - 2d(b + d)
    # * @ param
    # composite(a + c, b + d)
    # * @ param
    # vec(c, d)
    '''
    def refined_vector_value(self, composite, vec, sign):
        sum = 0.0
        if len(composite) == 0:
            composite = np.zeros_like(vec)
        if math.isnan(vec[0]):
            vec = np.zeros_like(vec)
        '''
        # for i,v in enumerate(vec):
        #     if math.isnan(v): v=0
        #     composite_value=composite[i]
        #     sum += math.pow(v, 2) + sign * 2 * composite_value * v
        改造成直接的矩阵计算
        '''
        sum = np.sum(np.power(vec, 2) + sign * 2 * composite * vec)
        return sum

    def saveResult(self, cluster):
        with open('./result/cluster_%s_%s.json' % ('hanlp', str(self.model)), 'w+', encoding='utf-8') as save_obj:
            for k in cluster:
                data = dict()
                # data["cluster_id"] = k[0]
                data["cluster_nums"] = len(k)
                data["cluster_docs"] = [{"doc_content": value} for index, value in
                                        enumerate(k)]
                json_obj = json.dumps(data, ensure_ascii=False)
                save_obj.write(json_obj)
                save_obj.write('\n')
'''
簇类，根据hanlp进行改造，但没有再改写SparseVector类，因为python的计算很方便，不需要
'''
class Cluster():

    def __init__(self):
        #所有向量
        self.documents_ = []
        #所有向量和，作为组合向量
        self.composite_ = []
        #判定准则值
        self.sectioned_gain_ = 0.0
        #再分簇
        self.sectioned_clusters_ = []
        #本簇质心
        self.centroid_ = []  # 质心

    '''
    用于优先队列比较用
    '''
    def __lt__(self, other):
        return other.sectioned_gain() <= self.sectioned_gain()

    def centroid_vector(self):
        if (len(self.documents_) > 0 and len(self.composite_) == 0):
            self.set_composite_vector()
        nrm = np.linalg.norm(self.composite_)
        centroid_ = self.composite_ / nrm
        return centroid_
    '''
    重计算组合向量
    '''
    def set_composite_vector(self):
        self.composite_.clear()
        self.composite_ = np.sum(self.documents_, axis=1)

    def composite_vector(self):
        return self.composite_

    def clear(self):
        self.documents_.clear()
        self.composite_ = []
        if (self.centroid_ != None):
            self.centroid_ = []
        if (self.sectioned_clusters_ != None):
            self.sectioned_clusters_.clear()
        self.sectioned_gain_ = 0.0

    def documents(self):
        return self.documents_

    '''
    加入向量，加入时进行归一化，并计算组合向量
    '''
    def add_document(self, doc):
        nrm = np.linalg.norm(doc[1])
        if nrm != 0:  # 有空的
            doc = (doc[0], doc[1] / nrm)
        else:
            doc = (doc[0], np.array(doc[1]))
        self.documents_.append(doc)
        if len(self.composite_) == 0:
            self.composite_ = np.zeros(len(doc[1]))
        if math.isnan(doc[1][0]) or math.isnan(self.composite_[0]):
            print(doc)
        self.composite_ = np.add(self.composite_, doc[1])

    '''
    当移动簇中向量时使用
    '''
    def remove_document(self, doc):
        self.documents_.remove(doc)
        self.composite_ = self.composite_ - doc[1]

    '''
    暂时没用
    '''
    def refresh(self):
        pass

    def sectioned_gain(self):
        return self.sectioned_gain_

    '''
    计算准则值，增幅
    每个子簇的组合向量（归一化）和比原簇组合向量（归一化）的增幅
    '''
    def set_sectioned_gain(self):
        gain = 0.0  # np.float32(0.0)
        if (self.sectioned_gain_ == 0 and len(self.sectioned_clusters_) > 1):
            for c in self.sectioned_clusters_:
                composite_vector = c.composite_vector()
                # norm=math.sqrt(np.sum(np.power(composite_vector, 2)))
                norm = np.linalg.norm(composite_vector)
                gain += norm
            composite_vector = self.composite_vector()
            norm = np.linalg.norm(composite_vector)  # math.sqrt(np.sum(np.power(composite_vector, 2)))
            gain -= norm
        self.sectioned_gain_ = gain

    def size(self):
        return len(self.documents_)

    def sectioned_clusters(self):
        return self.sectioned_clusters_

    '''
            k=2
            centroids质心
            dataSet向量总集
        '''

    def choose_smartly(self, k):
        centroids = []
        numSamples = len(self.documents_)  # dataSet.shape[0]
        closest = np.zeros(numSamples, dtype=np.float32)
        index = random.randint(0, numSamples - 1)  # initial center
        centroids.append(self.documents_[index])  # dataSet[index,:])#这只是向量，

        count = 1
        potential = 0.0

        # 每一个向量到这个随机质心的距离
        for i in range(numSamples):
            dist = 1 - self.similarity_cosine(self.documents_[i][1], self.documents_[index][1])
            potential = potential + dist
            closest[i] = dist

        # choose    each    center
        while (count < k):
            randval = random.random() * potential
            for i in range(numSamples):
                dist = closest[i]
                if randval <= dist:
                    break
                randval -= dist
            if (i == numSamples):
                i = i - 1
            centroids.append(self.documents_[i])
            count += 1
            if count >= k: break
            new_potential = 0.0
            for i_ in range(numSamples):
                dist = 1 - self.similarity_cosine(self.documents_[i_][1], self.documents_[i][1])
                min = closest[i_]
                if (dist < min):
                    closest[i_] = dist
                    min = dist
                new_potential += min
            potential = new_potential
        return centroids


    def similarity_cosine(self, vector1, vector2):
        # cos1 = np.sum(vector1*vector2)
        # cos21 = np.sqrt(sum(vector1**2))
        # cos22 = np.sqrt(sum(vector2**2))
        # similarity = cos1/float(cos21*cos22)
        similarity = np.inner(vector1, vector2)
        return similarity

    '''
    分簇，根据质心进行距离判断
    '''
    def section(self, nclusters):
        numSamples = len(self.documents_)
        if nclusters > numSamples:
            logging.error("传入聚类数目%d大于文档数量%d，已纠正为文档数量\n", nclusters, numSamples)
            nclusters = numSamples
        centroids = self.choose_smartly(nclusters)
        for i in range(nclusters):
            newCluster = Cluster()
            self.sectioned_clusters_.append(newCluster)

        for i in range(numSamples):
            max_similarity = -1.0
            max_index = 0
            for j, centroid in enumerate(centroids):
                similarity = self.similarity_cosine(self.documents_[i][1], centroid[1])
                # 这里就是判断更接近哪一个质心，就划分到质心所在簇
                if (max_similarity < similarity):
                    max_similarity = similarity
                    max_index = j
            self.sectioned_clusters_[max_index].add_document(self.documents_[i])


'''

'''
if __name__ == "__main__":
    analyzer = ClusterAnalyzer()
    analyzer.addDocument("赵一", "流行, 流行, 流行, 流行, 流行, 流行, 流行, 流行, 流行, 流行, 蓝调, 蓝调, 蓝调, 蓝调, 蓝调, 蓝调, 摇滚, 摇滚, 摇滚, 摇滚");
    analyzer.addDocument("钱二", "爵士, 爵士, 爵士, 爵士, 爵士, 爵士, 爵士, 爵士, 舞曲, 舞曲, 舞曲, 舞曲, 舞曲, 舞曲, 舞曲, 舞曲, 舞曲");
    analyzer.addDocument("张三", "古典, 古典, 古典, 古典, 民谣, 民谣, 民谣, 民谣");
    analyzer.addDocument("李四", "爵士, 爵士, 爵士, 爵士, 爵士, 爵士, 爵士, 爵士, 爵士, 金属, 金属, 舞曲, 舞曲, 舞曲, 舞曲, 舞曲, 舞曲");
    analyzer.addDocument("王五", "流行, 流行, 流行, 流行, 摇滚, 摇滚, 摇滚, 嘻哈, 嘻哈, 嘻哈");
    analyzer.addDocument("马六", "古典, 古典, 古典, 古典, 古典, 古典, 古典, 古典, 摇滚");
    analyzer.corpu2vector()
    print(analyzer.document_)

    result = analyzer.repeatedBisection(0,1)
    print(len(result), result)