'''
数据处理实用类
'''
import json
import random
import re

# import jsonpath
import jieba
from jieba import analyse, posseg
from zhon.hanzi import punctuation
import jieba.analyse

class TextProcess:

    stopwords=[]
    #初始化，加载自定义字典和停用词
    def __init__(self,dic='./resources/all_dict_2.txt',stop="./resources/stop.txt"):#jieba.dict.utf8.ner_all
        def stopwordslist(filepath):
            stopwords = [line.strip() for line in open(
                filepath, 'r', encoding='utf-8').readlines()]
            return stopwords

        TextProcess.stopwords = stopwordslist(stop)
        jieba.load_userdict(dic)

        # jieba.add_word('一带一路')

    '''移除括号内的信息，去除噪声'''

    @staticmethod
    def remove_noisy(content):
        p1 = re.compile(r'（[^）]*）')
        p2 = re.compile(r'\([^\)]*\)')
        return p2.sub('', p1.sub('', content))

    @staticmethod
    def cut(text):
        return jieba.cut(text)
    #分句
    @staticmethod
    def cut_sent(para,other=''):
        if(other==''):
            para = re.sub('([。！？\?])([^”])', r"\1\n\2", para)  # 单字符断句符
        else:
            para = re.sub('([ 。！？\?])([^”])', r"\1\n\2", para)  # 单字符断句符a
        para = re.sub('(\.{6})([^”])', r"\1\n\2", para)  # 英文省略号
        para = re.sub('(\…{2})([^”])', r"\1\n\2", para)  # 中文省略号
        # para = re.sub('(”)', '”\n', para)  # 把分句符\n放到双引号后，注意前面的几句都小心保留了双引号
        para = para.rstrip()  # 段尾如果有多余的\n就去掉它
        # 很多规则中会考虑分号;，但是这里我把它忽略不计，破折号、英文双引号等同样忽略，需要的再做些简单调整即可。
        return para.split("\n")

    #删除空行
    @classmethod
    def delSpace(self,line):
        line = re.sub('\n', '', line)
        line=line.strip()
        if not len(line):
            line=re.sub('\n', '', line)
        return line

    #删除数字
    @classmethod
    def delNum(self,line):
        return re.sub('[a-zA-Z0-9]', '', line)

    #删除标点
    @classmethod
    def delPunctuation(self,line):
        return re.sub(r"[%s]+" % punctuation, "", line)

    #删除HTML标签
    @classmethod
    def delHtml(self,line):
        return re.sub('</?\w+[^>]*>', '', line)

    #增加fasttext专用分类标签（含前缀）
    @classmethod
    def addLabel(self,content,categray,perfix="__label__"):
        return "\t"+perfix+" "+ content + "\t\n"

    #删除停用词
    @classmethod
    def delStop(self,linelist):
        outline = ""
        for word in linelist:
            if word not in self.stopwords:
                if word != '\t' or word != '\n':
                    outline += word
                    outline += " "
        return outline

    #合并删除运作
    @classmethod
    def doAll(self,content,ds=True,dn=True,dh=True,dst=True,dp=True):
        if(ds):
            content=self.delSpace(content)
        if(dp):
            content = self.delPunctuation(content)
        if(dn):
            content = self.delNum(content)
        if (dh):
            content = self.delHtml(content)
        if (dst):
            linelist= jieba.cut(content)
            content = self.delStop(linelist)
        return content

    #结巴的tfidf关键词抽取结果
    @staticmethod
    def tfidf(content,POS=()):
        return jieba.analyse.extract_tags(content,allowPOS=POS)

    @staticmethod
    def posseg(content, POS=[]):
        pos=posseg.cut(content)
        re=[]
        for x in pos:
           # print(x.word,x.flag)
           if x.flag in POS:
               re.append(x.word)
        return re

    # 结巴的tfidf关键词抽取结果
    @staticmethod
    def textrank(content,POS=()):
        return analyse.textrank(content, topK=20, withWeight=True, allowPOS=POS) #('nr', 'n')

    @classmethod
    def test(cls):
        t = "习近平在重庆调研时强调，创新、协调、绿色、开放、共享的发展理念，一带一路是在深刻总结国内外发展经验教训、分析国内外发展大势的基础上形成的，凝聚着对经济社会发展规律的深入思考，体现了“十三五”乃至更长时期我国的发展思路、发展方向、发展着力点。"
        TextProcess()
        print(TextProcess.doAll(t))
        print(TextProcess.tfidf(t,('n')))

    @classmethod
    def test1(cls):
        t = "他们之间儿虞我诈，他们之间尔虞我诈。"
        TextProcess()
        print(' '.join(TextProcess.cut(t)))



if __name__=='__main__':
    TextProcess.test1()