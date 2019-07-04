from difflib import SequenceMatcher

import whoosh
from whoosh.qparser import QueryParser
from whoosh.index import create_in
from whoosh.index import open_dir
from whoosh.fields import *
from jieba.analyse import ChineseAnalyzer
# from get_comment import SQL
from whoosh.sorting import FieldFacet

# analyser = ChineseAnalyzer()  # 导入中文分词工具
# schema = Schema(phone_name=TEXT(stored=True, analyzer=analyser), price=NUMERIC(stored=True),
#                 phoneid=ID(stored=True))  # 创建索引结构
# ix = create_in("path", schema=schema, indexname='indexname')  # path 为索引创建的地址，indexname为索引名称
# writer = ix.writer()
# writer.add_document(phone_name='name', price="1", phoneid="id")  # 此处为添加的内容
# print("建立完成一个索引")
# writer.commit()
# # 以上为建立索引的过程
# new_list = []
# index = open_dir("path", indexname='indexname')  # 读取建立好的索引
# with index.searcher() as searcher:
#     parser = QueryParser("phone_name", index.schema)
#     # whoosh.qparser
#     myquery = parser.parse("name")
#     facet = FieldFacet("price", reverse=True)  # 按序排列搜索结果
#     results = searcher.search(myquery, limit=None, sortedby=facet)  # limit为搜索结果的限制，默认为10，详见博客开头的官方文档
#     for result1 in results:
#         print(dict(result1))
#         new_list.append(dict(result1))
word='有令不行'
word1='止有令不'
# words=[]
# for i, char in enumerate(word):
#     # sames = self.same_stroke[char]
#
#     sames=['o','h']
#     # print(i,word[:i],word[(i+1):])
#     for same in sames:
#         words.append(word[:i] + same + word[(i + 1):])
# print(words)
print(set(word))
print(set(word) and set(word1))
print(set(word) & set(word1))
print(len(set(word) & set(word1))>len(word)*0.7)

print(SequenceMatcher(None,word, word).get_matching_blocks())
