# import xml.etree.ElementTree as ET
import glob
import linecache
import random
import re
from string import punctuation
from xml.dom.minidom import parse
import xml.dom.minidom as xmldom
import jieba
# def stopwordslist(filepath):
#     stopwords = [line.strip() for line in open(
#         filepath, 'r', encoding='utf-8').readlines()]
#     return stopwords
# stopwords = stopwordslist('./resources/stop.txt')
# jieba.load_userdict("./resources/userdict.txt")
#
#
# f = glob.glob('./resources/*.xml')
#
# fou=open('xijinping_fasttext.txt','w', encoding='UTF-8')
# for file in f:
#     print(file)
#     domboj = xmldom.parse(file)
#     rows=domboj.getElementsByTagName("row")
#     for row in rows:
#         title=row.getElementsByTagName("IR_URLTITLE")[0].firstChild.data
#         content=row.getElementsByTagName("IR_CONTENT")[0].firstChild.data
#         catalog=row.getElementsByTagName("IR_CATALOG")[0].firstChild.data
#         #标题
#         line=title.strip()+"  "+content.strip()
#         line = re.sub('[a-zA-Z0-9]', '', line)
#         line = re.sub('\n', '', line)
#         linelist = jieba.cut(re.sub(r"[%s]+" % punctuation, "", line), cut_all=False)
#         outline=""
#         for word in linelist:
#             if word not in stopwords:
#                 if word != '\t' or word!='\n':
#                     outline += word
#                     outline += " "
#         outline = "\t__label__" + catalog + "  "+ outline + "\t\n"
#         fou.write(outline)
# fou.close()

fou1=open('./resources/xijinping_fasttext.txt','w', encoding='UTF-8')
lines = linecache.getlines("./xijinping_fasttext.txt")
random.shuffle(lines)

fou1.writelines(lines)
# fin = open('xijinping.txt', mode='r', encoding='UTF-8')
# fou = open('xijinping1.txt', mode='w', encoding='UTF-8')
# for line in fin.readlines():
#     # 空行
#     line = line.strip()
#     if not len(line):
#         continue
#     line = re.sub('</?\w+[^>]*>', '', line)
#     newline = jieba.cut(line, cut_all=False)
#     fou.write(' '.join(newline) + '\n')
# fin.close()
# fou.close()