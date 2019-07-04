import linecache,re,zhon
from zhon.hanzi import punctuation
from gensim import corpora, models, similarities
import jieba

def stopwordslist(filepath):
    stopwords = [line.strip() for line in open(
        filepath, 'r', encoding='utf-8').readlines()]
    return stopwords
standard_data = []
stopwords = stopwordslist('./resources/stop.txt')
jieba.load_userdict("./resources/userdict.txt")

lines = linecache.getlines("./resources/xijinping3.txt")
#在分句之后，会出现很多重复项，要
for i, line in enumerate(lines):
    line = re.sub('[a-zA-Z0-9]', '', line)
    line = re.sub(r"[%s]+" % punctuation, "", line)
    standard_data.append(list(jieba.cut(line, cut_all=False)))

# 生成字典和向量语料

dictionary = corpora.Dictionary(standard_data)
dictionary.filter_extremes()
# dictionary.save("./mod/dic")
dictionary=corpora.Dictionary.load("./mod/dic")
print(dictionary.num_docs)

# 通过下面一句得到语料中每一篇文档对应的稀疏向量（这里是bow向量）
corpus = [dictionary.doc2bow(text) for text in standard_data]
print('corpus:',corpus[:20])

# corpus是一个返回bow向量的迭代器。下面代码将完成对corpus中出现的每一个特征的IDF值的统计工作
# tfidf_model = models.TfidfModel(corpus)
# tfidf_model.save("./mod/tfidf_model")
tfidf_model=models.TfidfModel.load("./mod/tfidf_model")
corpus_tfidf = tfidf_model[corpus]
print("corpus_tfidf")

####文档相似性的计算
map_value_user = {}

raw_data = [['环境','保护']]



# index = similarities.MatrixSimilarity(corpus_tfidf)
# index.save("index")
# vec_bow =[dictionary.doc2bow(text) for text in raw_data]   #把用户语料转为词包
# all_reult_sims = []
# times_v2 = 0



###对每个用户语聊与标准语聊计算相似度

# for i in vec_bow:
#      #直接使用上面得出的tf-idf 模型即可得出商品描述的tf-idf 值
#     sims = index[tfidf_model[i]]
#     sims = sorted(enumerate(sims), key=lambda item: -item[1])
# #     result_sims = []
#     for i,j in sims[:20]:
#         print(standard_data[i],i,j)
        # result_sims.append([map_value_user[times_v2],map_value[i],j])
#     times_v2 += 1
#     all_reult_sims.append(result_sims[:20])
# print(sims for sims in all_reult_sims)

####--------------------LSI-----------

# lsi = models.LsiModel(corpus_tfidf)
# lsi.save("./mod/lsi_model")
lsi=models.LsiModel.load("./mod/lsi_model")
corpus_lsi = lsi[corpus_tfidf]
print("corpus_lsi",lsi.num_topics)


# lda=models.LdaModel(corpus_tfidf)
# lda.save("./mod/lda_model")
# corpus_lda=lda[corpus_tfidf]
# similary=similarities.MatrixSimilarity(corpus_lda)


####文档相似性的计算
map_value_user = {}

# index = similarities.MatrixSimilarity(corpus_lsi)
# index.save("./mod/index")
index = similarities.MatrixSimilarity.load("./mod/index")

# vec_bow =dictionary.doc2bow(['环境','保护','绿水青山','开发']) #for text in raw_data   #把商品描述转为词包
vec_bow =dictionary.doc2bow(jieba.cut('消除贫困、改善民生、实现共同富裕，是社会主义的本质要求，是我们党的重要使命'))
vec_tfidf=tfidf_model[vec_bow]
vec_lsi1=lsi[vec_bow]
vec_lsi=lsi[vec_tfidf]
temp=[]
for xx in vec_lsi:
    temp.append(xx[1])
print(len(temp),lsi.num_topics)
temp=[]
for xx in vec_lsi1:
    temp.append(xx[1])
print(len(temp),lsi.num_topics)

sims=index[vec_lsi]
sims=sorted(enumerate(sims), key=lambda item: -item[1])


# vec_lda=lda[vec_tfidf]
# sims1=similary[vec_lda]
# sims1=sorted(enumerate(sims1), key=lambda item: -item[1])


# print(sims)
for i,j in sims[:5]:
    # print(lines[i],i)
    print(standard_data[i],i,j)
# print("----------lda----------\n")
# for i,j in sims1[:20]:
#     # print(lines[i],i)
#     print(standard_data[i],i,j)

doc=models.doc2vec