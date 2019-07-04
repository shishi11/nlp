# -*- coding: utf-8 -*-
import time

import pymysql
from py2neo import Graph, Node, Relationship, NodeMatcher,PropertyDict
import logging

import textProcess

logging.basicConfig(level=logging.INFO)  # ,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging = logging.getLogger(__name__)


graph = Graph("http://192.168.1.100:7474", username="neo4j", password='admin')
graph.delete_all()
# graph.merge()

'''
1 —— 创建node，函数第一个参数是节点类型，第二个参数是value值
'''
# a = Node('PersonTest', name='张三',key='s')
# b = Node('PersonTest', name='张三',key='s')
# # r = Relationship(a, 'KNOWNS', b)
# s = a | b #| r
# graph.create(s)

tx = graph.begin()
a = Node('PersonTest', name='张三',key='s')
b = Node('PersonTest', name='张三1',key='s1',age=33)
tx.merge(a,'PersonTest','name')
tx.merge(b,'PersonTest','name')

tx.commit()

# a['地点']=['sf','sff']
# graph.push(a)
# graph.
json={'中文名称': ['北京故宫博物院'], '历经朝代': ['明朝，清朝'], '地点': ['中国北京'], '外文名称': ['The Palace Museum'], '建议游玩时长': ['3-4小时'], '建馆时间': ['192\
5年10月10日'], '开放时间': ['8:00～17:00（周一闭馆）'], '竣工时间': ['明朝'], '类别': ['古代文化艺术博物馆'], '著名景点': ['午门,东华门,太和门三大殿'], '适宜季节': ['9月-10月'], '门票价格': ['旺季60.00元\
淡季40.00元&nbsp;'], '馆藏精品': ['清明上河图']}
# for key in json:
#     a[key]=json[key]
# graph.push(a)
class Neo4j():
    def __init__(self):
        self.tp= textProcess.TextProcess()
        self.graph = Graph("http://localhost:7474", username="neo4j", password='admin')
        self.graph.delete_all()

    def connect_db(self):
        return pymysql.connect(host='192.168.1.101',
                               port=3306,
                               user='root',
                               password='',
                               database='xinhua',
                               charset='utf8')

    def query_news(self, sql_str):
        logging.info(sql_str)
        con = self.connect_db()
        cur = con.cursor()
        cur.execute(sql_str)
        rows = cur.fetchall()
        cur.close()
        con.close()
        return rows

    def test(self):
        rows=self.query_news("select * from news limit 100")
        for row in rows:
            title = row[3]
            content = row[4]
            catalog = row[6]
            keywords=list(self.tp.tfidf(title+content))
            date= time.mktime(row[2].timetuple())
            date_str=row[2].strftime("%Y-%m-%d %H:%S:%M")
            tx = self.graph.begin()
            news = Node('news', title=title,content=content,date=date_str,catalog=catalog,url=row[5],mktime=date)
            # b = Node('PersonTest', name='张三1', key='s1', age=33)
            tx.merge(news, 'news', 'title')

            for k in keywords:
                keyword= Node('keyword',key=k)
                tx.merge(keyword, 'keyword', 'key')
                relation=Relationship(news,'include',keyword)
                tx.create(relation)
            tx.commit()

# neo=Neo4j()
# neo.test()
