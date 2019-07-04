import random
import re

import jieba
from fasttext import fasttext
import jieba.analyse
import _sqlite3
import textProcess

def readNews():
    conn=_sqlite3.connect('./resources/news0712.db')
    cursor=conn.cursor()
    news=cursor.execute("select * from news where title like '%习近平%'")
    news=[c for c in news]
    conn.close()
    return news

if __name__=='__main__':
    news=readNews()
    print(len(news))
    fou = open('./resources/xjpnews_ft_ccorpus1.txt', 'w', encoding='utf-8')
    fou1 = open('./resources/xjpnews_ft_other1.txt', 'w', encoding='utf-8')
    jieba.load_userdict('./resources/userdict.txt')
    classifier=fasttext.load_model("./mod/xjpnews_classifier_model1.bin",encoding='utf-8',label_prefix='__lable__')

    random.shuffle(news)
    textProcess.TextProcess()
    for news_ in news[:1000]:
        text=news_[3]+' '+news_[4]
        t1=textProcess.TextProcess.doAll(text)
        # print(t1,"\n")
        # texts= [' '.join(jieba.cut(text))]
        texts=[t1]
        # texts1=[' '.join(jieba.cut(text))]
        # texts2=[' '.join(jieba.cut(news_[3]))+' '.join(news_[8].split('|'))]
        lables=classifier.predict_proba(texts,k=1)
        # lables1=classifier.predict_proba(texts1,k=1)
        # lables2=classifier.predict_proba(texts2,k=1)

        if(lables[0][0][1]>0.99):#这部分是可以作为素材使用的
            # print(news_[3],'extracttage:',lables,"cut:",lables1,"org:",lables2,news_[6],'\n')
            if re.sub("__label__","",lables[0][0][0]) not in news_[6].split(','):
                print(lables[0][0][0] + " " + news_[3] + "\n",lables,re.sub("__label__","",lables[0][0][0]) ,news_[6])
            # fou.write(lables[0][0][0]+" "+t1+"\n")
        # else:
            # fou1.write(lables[0][0][0] + " " +t1 + "\n")

    fou.close()
    fou1.close()