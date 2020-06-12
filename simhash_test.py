# -*- coding: utf-8 -*-
"""
Created on Mon May 19 09:32:00 2018

@author: wangyao
"""
import jieba
# simhash值直接用包计算，pip install simhash
from simhash import Simhash
import re
import numpy as np
import pandas as pd

# 停用词
stopwords = [line.strip() for line in open('./resources/stop.txt', 'r', encoding='utf-8').readlines()]


# 文本预处理+特征提取
def get_features(s):
    width = 3
    string = ''
    s = re.sub(r'[^\w]+', '', s)
    s = jieba.lcut(s)
    X, Y = ['\u4e00', '\u9fa5']
    s = [i for i in s if len(i) > 1 and X <= i <= Y and i not in stopwords]
    for i in s:
        string += i
    if string:
        return [string[i:i + width] for i in range(max(len(string) - width + 1, 1))]
    else:
        print("请输入中文文档")


# list1 = df.content.apply(lambda x: isinstance(x, str))

# 文本预处理
def Pre_Processing(s):
    string = ''
    s = re.sub(r'[^\w]+', '', s)
    s = jieba.lcut(s)
    X, Y = ['\u4e00', '\u9fa5']
    s = [i for i in s if len(i) > 1 and X <= i <= Y and i not in stopwords]
    string = string.join(s)
    if string:
        return string
    else:
        print('请勿输入空字符串或者完全由停用词组成的无意义的句子')


# simhas包自带的汉明距离
def hanming_simhash(s1, s2):
    hanmingdistance = Simhash(Pre_Processing(s1)).distance(Simhash(Pre_Processing(s2)))
    # return hanming_distance
    return 1 - hanmingdistance / 64


# 将字符串转化为hashcode
def ToSimhashcode(s):
    if type(s) == str:
        return Simhash(get_features(s)).value
    else:
        print('输入的句子格式需要是字符串')


# 自己写的汉明距离
def hanming_distance(s1, s2):
    if type(s1) == str and type(s2) == str:
        hanmingdistance = bin(
            int(hex(Simhash(get_features(s1)).value), 16) ^ int(hex(Simhash(get_features(s2)).value), 16)).count('1')
    elif type(s1) == int and type(s2) == int:
        hanmingdistance = bin(int(hex(s1), 16) ^ int(hex(s2), 16)).count('1')
    else:
        print('s1和s2需要是相同的数据类型！')
    # return hanming_distance
    return 1 - hanmingdistance / 64


# 直接填入文本列表，生成相似度矩阵（文本较少的时候可以使用此函数）
def simhash_simmatrix_doc(doc_list):
    simhash_corpus = []
    for i in range(len(doc_list)):
        simhash_corpus.append([])
    for i in range(len(doc_list)):
        print(i)
        for j in range(i, len(doc_list)):
            simhash_corpus[j].append(hanming_distance(doc_list[i], doc_list[j]))
    x = len(simhash_corpus) - 1
    for i in range(len(simhash_corpus) - 1):
        simhash_corpus[i].extend(x * [0])
        x = x - 1
    return np.array(simhash_corpus) + np.array(simhash_corpus).T


# 填入文本的hashcode，生成相似度矩阵
def simhash_simmatrix_hashcode(hashcode_list):
    simhash_corpus = []
    for i in range(len(hashcode_list)):
        simhash_corpus.append([])
    for i in range(len(hashcode_list)):
        print(i)
        for j in range(i, len(hashcode_list)):
            simhash_corpus[j].append(hanming_distance(hashcode_list[i], hashcode_list[j]))
    x = len(simhash_corpus) - 1
    for i in range(len(simhash_corpus) - 1):
        simhash_corpus[i].extend(x * [0])
        x = x - 1
    return np.array(simhash_corpus) + np.array(simhash_corpus).T


# 过滤文本生成的相似度矩阵，
def DuplicateContent_filtering_doc(doc_list, sim=0.8):
    if sim > 1 or sim < 0:
        print('错误的取值范围！！范围应该是[0,1]')
    sim_matrix = simhash_simmatrix_doc(doc_list) > sim
    return sim_matrix


# 过滤hashcode生成的相似度矩阵
def DuplicateContent_label_hashcode(hashcode_array, sim=0.8):
    if sim > 1 or sim < 0:
        print('错误的取值范围！！范围应该是[0,1]')
    sim_matrix = hashcode_array > sim
    return sim_matrix


# 列表求交集
def list_intersection(list1, list2):
    list3 = list(set(list1) & set(list2))
    return list3


# 清洗重复的文章列表
def clean_Duplicate_List(Duplicate_List):
    Duplicate_List = [list(set(i)) for i in Duplicate_List]
    Duplicate = []
    for i in range(len(Duplicate_List)):
        temp = []
        for j in range(len(Duplicate_List)):
            if list_intersection(Duplicate_List[i], Duplicate_List[j]) != []:
                temp.extend(Duplicate_List[i])
                temp.extend(Duplicate_List[j])
        Duplicate.append(temp)
    Duplicate = [list(set(i)) for i in Duplicate]
    NoDuplicate = []
    for i in Duplicate:
        if i in NoDuplicate:
            pass
        else:
            NoDuplicate.append(i)
    NoDuplicate = [list(set(i)) for i in NoDuplicate]
    return NoDuplicate


# 读入相似度矩阵，返回非重复的文章ID和重复的文章ID
def DuplicateContent_filtering_hashcode(matrix):
    NoDuplicateList = []
    DuplicateList = []
    NoDuplicate_List = []
    Duplicate_List = []
    for i in range(len(matrix)):
        DuplicateList.append([])
    for i in range(len(matrix)):
        NoDuplicateList.append([])
        if (matrix[i] == True).sum() <= 1:
            NoDuplicateList[i].append(ID[i])
        else:
            for j in range(len(matrix[i])):
                if matrix[i][j] == True and i < j:
                    DuplicateList[i].extend([i, j])
    for i in DuplicateList:
        if i != []:
            Duplicate_List.append(i)
    else:
        pass
    for i in NoDuplicateList:
        if i != []:
            NoDuplicate_List.append(i)
    else:
        pass
    return NoDuplicate_List, clean_Duplicate_List(Duplicate_List)

if __name__ == '__main__':
    code=ToSimhashcode('我是一个好人咧')
    print(code)
    code = ToSimhashcode('我是一个好人')
    print(code)