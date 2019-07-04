import _sqlite3
import linecache
import re

import jieba
import sklearn
import zhon
from jieba import analyse, posseg
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from zhon.hanzi import punctuation

nts=set()

def readNation():
    conn=_sqlite3.connect('./resources/region_city.db')
    cursor=conn.cursor()
    nations=cursor.execute("select name from region_city where level=2")
    nation=[c[0] for c in nations]
    conn.close()
    return nation

def addNation():
    for n in nations:
        jieba.add_word(word=n,tag='ns')

def initTuple():
    jieba.load_userdict('./resources/userdict.txt')


    addNation()
    lines = linecache.getlines('./resources/nation_tuple.txt')
    for line in lines:
        nsnr=tuple(line.strip().split(" "))
        nts.add(nsnr)
        jieba.add_word(nsnr[2].strip(),tag='nr') #补一些人工修改过的人名


def addTupleFromFile(file):

    lines=linecache.getlines(file)
    for line in lines:
        addTuple_(line)

    writeTupleFile()

def writeTupleFile():
    print(nts)
    nts1=list(nts)
    # nts1.extend(tup)
    # nts1=list(set(nts1))
    nts1.sort(key=lambda it:it[0])
    print(nts1)
    fou = open('./resources/nation_tuple.txt', 'w', encoding='UTF-8')
    for t in nts1:
        if(t[0] in nations):
            # ns,n,nr=t
            fou.write(' '.join(t)+'\n')
    fou.close()

def addTuple(line):
    li = list(posseg.cut(line))
    n = 0
    for x in li:
        if (x.flag == 'ns'):
            if (n + 2 < len(li)):
                if (li[n + 1].flag == 'n' and li[n + 2].flag == 'nr'):
                    nts.add((x.word, li[n + 1].word, li[n + 2].word))
        n += 1

def addTuple_(line):
    li = list(posseg.cut(line))
    #应该 再分句
    _word_ngrams(li)


def addTupleFromDb():
    conn = _sqlite3.connect('./resources/news0712.db')
    cursor = conn.cursor()
    news = cursor.execute("select detail from news")
    news = [c[0] for c in news]
    conn.close()
    for details in news:
        detail=details.split("\n")
        for line in detail:
            addTuple_(line)
    writeTupleFile()

def meeting():
    pass

#tokens给出元组模式，用tuple_pattern来处理模板，为提高效率可以多个模板并行
#要在之前就进行分句，进来的来要超句
def _word_ngrams(tokens,stop_words=None,minChar=2,tuple_pattern=['[nations]','[n]','[nr]'],mints=3,maxts=3):
    #以数组字典模式返回
    wtuples=[]

    #去掉停用词
    if stop_words is not None:
        tokens=[(word,flag) for (word,flag) in tokens if word not in stop_words]

    # 句子不能过短
    n = len(tokens)
    if n < 3: return wtuples

    #分离词性和词本身
    nsnr, ws = [flag for word, flag in tokens], [word for word, flag in tokens]

    #从第一个词到倒数第二个词
    for i in jieba.xrange(0, n - 2, 1):

        # temp_intentions=tuple_intentions

        #这里要可变长，全句长，直到X
        for num in jieba.xrange(3, n - i + 1):
            #每个变长组
            wtuple = tokens[i:i + num]
            w= ws[i:i+num]
            f= nsnr[i:i+num]
            tlen=len(w)
            #隔过标点符号 和 词过短的情况（暂默认为2，每个词应该由2个以上字组成）
            if 'x' not in f and all(len(w_)>=minChar for w_ in w):
                flag=True
                current_intention=None
                # 一句话应该会符合多个意图，但一个词组应该只符合一个意图#意图循环
                #这里的intention是一个key
                for intention in tuple_intentions:
                    flag_=True
                    pindex=0
                    #第几个字循环，
                    for index,val in enumerate(w):
                        #把这个词的本体和词性、位置 参数 给意图模板
                        #如果不管从词组的哪一个词开始不符合模板，则跳出意图
                        if not isInPattern(wtuple[index],intention,index,tlen,pindex):
                            flag_=False
                            break
                        if tuple_intentions[intention][pindex][-1]!='+':
                            pindex+=1
                    if flag_:
                        #如果每个词都符合这个意图
                        current_intention = intention
                        wtuples.append({intention:wtuple})
                #一个词组应该只符合一个意图
                if current_intention:
                    break
                    #nts.add((wtuple[0].word,wtuple[1].word,wtuple[2].word))
    return wtuples

'''
判断某个词是不是匹配模板
可以是指定字，直接写
可以指定词性  [n]
可以指定枚举列表   [nation] ----先加载地名库国家名数据-----此处可无限扩充（类似unit）
这里还应该可以处理归一化问题，可通过对模板的变形认知要识别的分词，类似于UNIT，但增加了词性识别
这里还应该可以分层，分层处理，看怎么模块化吧
'''
def isInPattern(wpos,intension,index,tlen):
    patterns=tuple_intentions[intension]
    #['出席','[n]+','[meetings]']
    if len(patterns)<=index:
        pattern=patterns[index]
    else:
        pattern=patterns[-2]
        if pattern[-1] != '+': return False
    if re.match('\[\w+\]',pattern):
        # if pattern[-1]=='+':

        #[]
        if p in tuple_patterns:
            return wpos.word in tuple_patterns[p]
            # if p=='[nation]':
            #     return wpos.word in nations
            # if p=='[mettings]':
            #     return wpos.word in mettings
    # elif re.match('\[\w+\]',p):
        if "["+wpos.flag+"]"==p:
            return True
        else:
            return False
    elif wpos.word==p:
         return True
    return False

def longWord():
    # vec = CountVectorizer(ngram_range=(5, 10),decode_error='ignore' ,token_pattern=r'\w',max_features=10)


    vec1=TfidfVectorizer(ngram_range=(1, 1),decode_error='ignore' ,max_features=10,token_pattern=r'\b\w\w\w\w\w\w+[，。！？；]\b',)

    lines=linecache.getlines('./resources/xijinping3.txt')
    vec1.fit_transform(lines)
    # linescut=[]
    # for s in lines:
    #     line=jieba.cut(s)
    #     linescut.append(' '.join(list(line)))
    # vec1.fit_transform(linescut)

    # print()
    # vec1 = CountVectorizer(ngram_range=(1, 1),decode_error='ignore',token_pattern=r'\b\w+\b')
    # x=vec.fit_transform([' '.join(ws)])
    # print(vec.get_feature_names())
    print('-------------',vec1.get_feature_names())
    print('-------------', vec1.vocabulary_)



def test():
    text = "c"

    li=list(posseg.cut(text))
    # nsnr,ws = [flag for word,flag in li],[word for word,flag in li]
    print(li)
    # n = len(li)
    # for i in jieba.xrange(0, n - 2, 1):
    #     wtuple = li[i:i + 3]
    #     w= ws[i:i+3]
    #     f= nsnr[i:i+3]
    #     if 'x' not in f:
    #     # if not re.match(r"[%s]+" %punctuation,' '.join(w) ) :
    #         print(wtuple)
    # print(_word_ngrams(list(posseg.cut(text))))


    # ws=list(jieba.cut(text))
    # vec=CountVectorizer(ngram_range=(3,3),)
    # vec1 = CountVectorizer(ngram_range=(1, 1),decode_error='ignore',token_pattern=r'\b\w+\b')
    # x=vec.fit_transform([' '.join(ws)])
    # print(vec.get_feature_names())
    #
    # vec1.fit_transform([' '.join(nsnr)])
    # print(vec1.get_feature_names())
    # print(type(li[0]))
    # print(" ".join(li('flag')))



if __name__=='__main__':
    # 在这里加入各种实体词

    nations = readNation()

    meetings = ['会', '会议','论坛']
    #用字典放各类实体词典
    tuple_patterns = {'[nations]':nations, '[meetings]':meetings}
    initTuple()

    tuple_intentions ={'nation':['[nations]','[n]','[nr]'],
                       'meeting':['出席','[n]+','[meetings]']}
    # addTupleFromFile("./resources/xijinping3.txt")
    # addTupleFromDb()
    # jieba.add_word('生活富裕',tag='zy')#照此是可以再分词的，只要把指定的词给一个指定的值
    # posseg.load_model()
    # test()
    # print(nts)
    # print(re.match('\[\w+\]','[n]'))
    # p='[n]'
    # print(p.split('[]'))
    # longWord()

    s = list(jieba.posseg.cut('在华盛顿期间，习主席还先后会见了前来参加本届核安全峰会的丹麦首相拉斯穆森、韩国总统朴槿惠和阿根廷总统马克里，并出席了伊核问题六国机制领导人会议'))
    # print(s)
    # n=len(s)
    # for i in jieba.xrange(0, n - 2, 1):
    #
    #     for i_ in jieba.xrange(3, n-i+1):
    #         print(i,i_,s[i:i+i_])
    # print(tuple_intentions['nation'])
    # for i in reversed(tuple_intentions):
    #     print(i)
    # print(re.match('\[\w+\]','[n]+'))

    # print(_word_ngrams(s))
    print("sdfasdfa"[-1])