import glob
import logging

import pymysql
from fasttext import fasttext
from gensim import corpora
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer, TfidfVectorizer
from sklearn.metrics import classification_report
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import SVC

from textProcess import TextProcess
import numpy as np


# import fasttext

def connect_wxremit_db():
    return pymysql.connect(host='127.0.0.1',
                           port=3306,
                           user='root',
                           password='',
                           database='xinhua',
                           charset='utf8')


def query_country_name(cc2):
    sql_str = ("SELECT *"
               + " FROM news_"
               + " WHERE detail like '%s' and topic='%s'" % ('%习近平%', cc2))
    logging.info(sql_str)

    con = connect_wxremit_db()
    cur = con.cursor()
    cur.execute(sql_str)
    rows = cur.fetchall()
    cur.close()
    con.close()

    # assert len(rows) == 1, 'Fatal error: country_code does not exists!'
    return rows

def query_all(cc2):
    sql_str = ("SELECT *"
               + " FROM news_"
               + " WHERE  detail like '%s'" % cc2
               +" LIMIT 100")
    logging.info(sql_str)

    con = connect_wxremit_db()
    cur = con.cursor()
    cur.execute(sql_str)
    rows = cur.fetchall()
    cur.close()
    con.close()

    # assert len(rows) == 1, 'Fatal error: country_code does not exists!'
    return rows

def create_temp(cat_keyword):
    fou = open('./resources/news_fasttext_all.txt', 'w', encoding='UTF-8')
    con = connect_wxremit_db()
    # cur = con.cursor()
    # cur.execute('TRUNCATE table news_temp')

    sql_str = "SELECT * FROM news_ WHERE detail like '%s' " % '%习近平%'
    cur = con.cursor()
    cur.execute(sql_str)
    rows = cur.fetchall()
    for row in rows:
        flag = False
        for topic in cat_keyword:
            catalog=topic

            title = row[3]
            content = row[4]

            line = title.strip() + "  " + content.strip()
            outline = TextProcess.doAll(line)

            for keyword in cat_keyword[topic]:
                if( outline.find(keyword)>-1):
                    flag=True
                    break
            if flag:
                outline = "\t__label__" + catalog + "  " + outline + "\t\n"
                fou.write(outline)
                break
        if not flag:
            catalog='其它'
            outline = "\t__label__" + catalog + "  " + outline + "\t\n"
            fou.write(outline)



    cur.close()
    fou.close()
    con.close()


def getTrainData(sql, param):
    sql_str = (sql % param)
    logging.info(sql_str)

    con = connect_wxremit_db()
    cur = con.cursor()
    cur.execute(sql_str)
    rows = cur.fetchall()
    cur.close()
    con.close()

    # assert len(rows) == 1, 'Fatal error: country_code does not exists!'
    return rows


def genfast(rows,outfile):
    fou = open(outfile, 'w', encoding='UTF-8')
    # for file in f:
    # print(file)
    # domboj = xmldom.parse(file)
    # rows=domboj.getElementsByTagName("row")
    TextProcess()
    for row in rows:
        title = row[3]
        content = row[4]
        catalog = row[9]
        if catalog is None:
            catalog='other'
        elif catalog.find('扶贫') > -1:
            catalog = 'fupin'
        elif catalog.find('环保')>-1:
            catalog='huanbao'


        # catalog = 'other' if row[9] is None else 'huanbao'

        # print(title,catalog)
        line = title.strip() + "  " + content.strip()
        outline = TextProcess.doAll(line)
        outline = "\t__label__" + catalog + "  " + outline + "\t\n"
        fou.write(outline)
    fou.close()


'''
处理原始数据，
1.先生成原始文本----已在库中
2.对原始文件生成fasttext标签
3.对原始文本生成tfidf词向量(没做)
4.对数据进行测试
5.对另外的数据进行初步试验
经过去停用词等工作，
'''


def process():
    cats = ['环保', '扶贫', '反腐', '一带一路', '人类命运共同体', '经济发展', '先进人物学习表彰', '国企改革', '创新发展', '教育',
            '强军', '慰问', '农村工作', '瞻仰缅怀', '国事外交', '哀悼送别', '党建', '纪念', '安全生产', '祖国统一', '统一战线',
            '依法治国', '科学技术', '强险救灾', '案件指示', '旅游', '一般会议', '妇女工作']
    cat_dict= {'环保':'huanbao', '扶贫':'fupin', '反腐':'fanfu', '一带一路':'yidayilu', '人类命运共同体':'gongtongti', '经济发展':'jingji', '先进人物学习表彰':'biaozhang', '国企改革':'guoqi', '创新发展':'chuangxin', '教育':'jiaoyu',
            '强军':'qiangjun', '慰问':'weiwen', '农村工作':'nongcun', '瞻仰缅怀':'zhanyang', '国事外交':'waijiao', '哀悼送别':'aidao', '党建':'dangjian', '纪念':'jinian', '安全生产':'anquan', '祖国统一':'zuguo', '统一战线':'tongyi',
            '依法治国':'yifa', '科学技术':'kexue', '强险救灾':'jiuzai', '案件指示':'anjian', '旅游':'lvyou', '一般会议':'huiyi', '妇女工作':'funv'}
    cat_keyword={
        '环保':['环保','环境保护'],
        '扶贫': ['扶贫', '脱贫'],
        '反腐': ['反腐', '腐败'],
        '一带一路':['一带一路'],
        '强军': ['军队', '部队'],
    }
    create_temp(cat_keyword)
    # db_data = query_country_name('环保')

    # 现在只要fasttext专用
    # genfast(db_data)


def test():
    data = query_country_name('环保')
    # TextProcess()
    for r in data:
        # print(r['id'])
        yield '%s %s Topic:\n' % (r[0], r[3])


def tfidf():
    data = query_country_name('环保')
    TextProcess()
    # step 1
    vectorizer = CountVectorizer(min_df=1, max_df=1.0, token_pattern='\\b\\w+\\b')
    corpus = [TextProcess.doAll(r[3] + r[4]) for r in data]

    transformer = TfidfTransformer()
    corpus_train = vectorizer.fit_transform(corpus)
    tfidf = transformer.fit_transform(corpus_train)
    words = vectorizer.get_feature_names()
    words = np.array(words)

    # transformer.fit() vectorizer.fit_transform(corpus)
    weight = tfidf.toarray()
    word_index = np.argsort(-weight)

    words_ = words[word_index]
    print(words_[:3][:3])

    for word in words:
        print(word)
    # ids=test()
    # for (id, w) in zip(ids, weight):
    #     print(u'{}:'.format(id))
    #     loc = np.argsort(-w)
    #     for i in range(5):
    #         print(u'-{}: {} {}'.format(str(i + 1), words[loc[i]], w[loc[i]]))
    #     print('\n')


def ft():
    saveDataFile = r'./resources/news_fasttext_all.txt'
    testFile=r'./resources/news_fasttext_环保扶贫1.txt'
    classifier=fasttext.supervised(saveDataFile, output='./mod/xjpnews_classifier_model3',dim=200,min_count=1,ws=10,epoch=150,neg=5,word_ngrams=2,bucket=1)
    # classifier = fasttext.load_model("./mod/xjpnews_classifier_model3.bin", encoding='utf-8', label_prefix='__lable__')
    # fasttext
    # fasttext.supervised().
    result = classifier.test(testFile)
    print("P@1:", result.precision)  # 准确率
    print("R@2:", result.recall)  # 召回率
    print("Number of examples:", result.nexamples)  # 预测错的例子
    texts='不谋全局者，不足谋一域。”2016年7月至今，以绿色税收等措施为发力点，政策力度持续增强。十九大报告亦指出，“必须树立和践行绿水青山就是金山银山的理念”“实行最严格的生态制度”。从经济学视角看环境治理，我们认为，“严监管”不仅有利于生态文明，更在三个层面牵动改革全局，促进中国经济转型升级。'
    texts1='水是指经济环境、制度环境；鱼是企业。他问如果“水”不好、中国的经济很差、中国不适合办企业，那么115家世界500强怎么来的？如果说“水”很好，那么为什么那么多“鱼”非正常死掉？今天很多的企业家在改革开放近40年里在这个国家赚了很多的钱，但他们移民了。2016年，美国的投资移民签了800个人，很多是咱们中国人。他们为什么要移民？这个焦虑是从何而来？这个问题在很多人的心目中仍是一个问号。'
    TextProcess()

    texts=[TextProcess.doAll(texts)]
    texts1=[TextProcess.doAll(texts1)]
    lables = classifier.predict_proba(texts,k=2)
    print(lables,texts)
    lables1 = classifier.predict_proba(texts1, k=2)
    print(lables1,texts1)

    # import xml.dom.minidom as xmldom
    # f = glob.glob('./resources/*.xml')
    # fou = open('./resources/xijinping_fasttext_predict.txt', 'w', encoding='UTF-8')
    # for file in f:
    #     print(file)
    #     domboj = xmldom.parse(file)
    #     rows=domboj.getElementsByTagName("row")
    #     for row in rows:
    #         title=row.getElementsByTagName("IR_URLTITLE")[0].firstChild.data
    #         content=row.getElementsByTagName("IR_CONTENT")[0].firstChild.data
    #         # catalog=row.getElementsByTagName("IR_CATALOG")[0].firstChild.data
    #         #标题
    #         line=title.strip()+"  "+content.strip()
    #         newsline=TextProcess.doAll(line)
    #         lables = classifier.predict([newsline])
    #         outline = "\t" + lables[0][0] + "  " + newsline + "\t\n"
    #         fou.write(outline)
    #
    # fou.close()

    # fou = open('./resources/news_fasttext_predict2.txt', 'w', encoding='UTF-8')
    # rows=query_all('%生态%')
    # for row in rows:
    #     title = row[3]
    #     content = row[4]
    #     line = title.strip() + "  " + content.strip()
    #     newsline = TextProcess.doAll(line)
    #     lables = classifier.predict_proba([newsline],k=2)
    #     outline = "\t__label__"
    #     fou.write(outline)
    #     if (len(lables) == 1):
    #         fou.write(lables[0][0][0]+str(lables[0][0][1]))
    #     if(len(lables[0])==2):
    #         fou.write(lables[0][1][0]+str(lables[0][1][1]))
    #     fou.write('   '+line + "\t\n")
    # fou.close()
    return
    #


def gensim():
    data = query_country_name('环保')
    # 词频统计
    TextProcess()
    # from collections import defaultdict
    # frequency = defaultdict(int)
    # for r in data:
    #    text= (TextProcess.doAll(r[3] + r[4])).split()
    #    for token in text:
    #         frequency[token] += 1
    # print(frequency)

    corpus = [(TextProcess.doAll(r[3] + r[4])).split() for r in data]
    dictionary = corpora.Dictionary(corpus)
    print(dictionary.dfs)


def NB():
    data = getTrainData("SELECT *"
                        + " FROM news_"
                        + " WHERE detail like '%s'", '%习近平%')
    TextProcess()
    X_train = [TextProcess.doAll(r[3] + r[4]) for r in data]

    y_train = [1 if r[9] == '环保' else 0 for r in data]

    vectorizer = CountVectorizer(min_df=1, max_df=1.0, token_pattern='\\b\\w+\\b')
    # vectorizer=TfidfVectorizer(token_pattern=,)
    X_count_train = vectorizer.fit_transform(X_train)

    mnb_count = MultinomialNB()
    svm_ = SVC(kernel='rbf')
    mnb_count.fit(X_count_train, y_train)
    svm_.fit(X_count_train, y_train)

    data1 = getTrainData("SELECT *"
                         + " FROM news_"
                         + " WHERE detail not like '%s'", '%习近平%')
    X_test = [TextProcess.doAll(r[3] + r[4]) for r in data1]
    X_count_test = vectorizer.transform(X_test)
    y_test = [1 if r[9] == '环保' else 0 for r in data1]

    y_predict = mnb_count.predict(X_count_test)
    y_predict1 = svm_.predict(X_count_test)
    print(classification_report(y_test, y_predict))  # , target_names=news.target_names))
    print(classification_report(y_test, y_predict1))


if __name__ == '__main__':
    # print(query_country_name('环保'))
    # process()
    # t=test()
    # print(list(t))
    # tfidf()
    # gensim()
    # NB()
    # data = getTrainData("SELECT *"
    #                     + " FROM news_"
    #                     + " WHERE detail not like '%s'", '%习近平%')
    # genfast(data,'./resources/news_fasttext_环保扶贫1.txt')
    # ft()
    # process()
    # ft()
    print(query_all('%会%'))