import json
import random
import re

import jsonpath
import jieba
from zhon.hanzi import punctuation
import jieba.analyse

def stopwordslist(filepath):
    stopwords = [line.strip() for line in open(
        filepath, 'r', encoding='utf-8').readlines()]
    return stopwords
stopwords = stopwordslist('./resources/stop.txt')
jieba.load_userdict("./resources/userdict.txt")

fou=open('./resources/xjpnews_fasttext.txt','w',encoding='utf-8')

f=open('./resources/data.txt',encoding='utf-8')
js=json.load(f)
f.close()
jsonp=jsonpath.jsonpath(js,"$..news.*")
random.shuffle(jsonp)



for el in jsonp:
    print(el['cat'],el['title'])
    # 标题
    line = el['title'].strip() + "  " + el['detail'].strip()
    line = re.sub('[a-zA-Z0-9]', '', line)
    line = re.sub('\n', '', line)
    linelist = jieba.cut(re.sub(r"[%s]+" % punctuation, "", line), cut_all=False)
    # linelist = jieba.analyse.extract_tags(re.sub(r"[%s]+" % punctuation, "", line))   #不应该 用这个，有ngram，有局部顺序
    outline = ""
    for word in linelist:
        if word not in stopwords:
            if word != '\t' or word != '\n':
                outline += word
                outline += " "
    outline = "\t__label__" + el['cat'] + "  " + outline + "\t\n"
    fou.write(outline)
fou.close()