# -*- coding:utf-8 -*-
import pandas as pd
import random
import fasttext
import jieba
import jieba.analyse
from sklearn.model_selection import train_test_split

import textProcess

if __name__=="__main__":
    # stopwordsFile=r"./data/stopwords.txt"
    # stopwords=getStopWords(stopwordsFile)
    saveDataFile=r'./resources/xjpnews_fasttext.txt'
    # saveDataFile1 = r'./resources/xjpnews_fasttext1.txt'#这是错误的，原理不对
    saveDataFile2 = r'./resources/xjpnews_ft_ccorpus1.txt'
    saveDataFile3 = r'./resources/xjpnews_ft_other1.txt'

    # preprocessData(stopwords,saveDataFile)
    #fasttext.supervised():有监督的学习
    '''
    input_file     			training file path (required)
output         			output file path (required)
label_prefix   			label prefix ['__label__']
lr             			learning rate [0.1]
lr_update_rate 			change the rate of updates for the learning rate [100]
dim            			size of word vectors [100]
ws             			size of the context window [5]
epoch          			number of epochs [5]
min_count      			minimal number of word occurences [1]
neg            			number of negatives sampled [5]
word_ngrams    			max length of word ngram [1]
loss           			loss function {ns, hs, softmax} [softmax]
bucket         			number of buckets [0]
minn           			min length of char ngram [0]
maxn           			max length of char ngram [0]
thread         			number of threads [12]
t              			sampling threshold [0.0001]
silent         			disable the log output from the C++ extension [1]
encoding       			specify input_file encoding [utf-8]
pretrained_vectors		pretrained word vectors (.vec file) for supervised learning []

    '''

    classifier=fasttext.supervised(saveDataFile, output='./mod/xjpnews_classifier_model1',dim=200,min_count=1,ws=10,epoch=150,neg=5,word_ngrams=2,bucket=1)#, label_prefix='__lable__'  dim=200,min_count=1,ws=10,epoch=150,neg=4
    # classifier=fasttext.load_model("./mod/xjpnews_classifier_model.bin",encoding='utf-8',label_prefix='__lable__')

    # fasttext.load_model()
    # saveDataFile2
    result = classifier.test(saveDataFile)
    print("P@1:",result.precision)    #准确率
    print("R@2:",result.recall)    #召回率
    print("Number of examples:",result.nexamples)    #预测错的例子

    #实际预测
    # lable_to_cate={1:'technology',1:'car',3:'entertainment',4:'military',5:'sports'}

    # texts=['中新网 日电 2018 预赛 亚洲区 强赛 中国队 韩国队 较量 比赛 上半场 分钟 主场 作战 中国队 率先 打破 场上 僵局 利用 角球 机会 大宝 前点 攻门 得手 中国队 领先']
    text=open('./resources/temp.txt','r').read()
    # text="新华社推出“习近平新时代中国特色社会主义思想在基层”系列调研报道"
    text1="习近平在十九届中央纪委二次全会上发表重要讲话强调全面贯彻落实党的十九大精神以永远在路上的执着把从严治党引向深入栗战书汪洋王沪宁韩正出席会议赵乐际主持会议新华社北京1月11日电中共中央总书记、国家主席、中央军委主席习近平11日上午在中国共产党第十九届中央纪律检查委员会第二次全体会议上发表重要讲话"
    # test= jieba.cut(text)
    # test=
    textProcess.TextProcess()
    jieba.load_userdict('./resources/xjpdict.txt')
    jieba.analyse.set_stop_words('./resources/stop.txt')
    text=textProcess.TextProcess.doAll(text)
    # test=jieba.cut(text)
    # test1=jieba.analyse.extract_tags(text,topK=100,allowPOS={'n','ns','nr','v','l'})
    # textProcess.TextProcess()
    texts=[text]

    # texts=[' '.join(test),' '.join(test1)]
    print(texts)
    lables=classifier.predict(texts)
    print(lables)
    # print(lable_to_cate[int(lables[0][0])])

    #还可以得到类别+概率
    lables=classifier.predict_proba(texts)
    print(lables)

    #还可以得到前k个类别
    lables=classifier.predict(texts,k=8)
    print(lables)

    #还可以得到前k个类别+概率
    lables=classifier.predict_proba(texts,k=8)
    print(lables)