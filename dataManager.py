# -*- coding: utf-8 -*

'''
数据管理类，把数据库部分拿出来

'''
import pymysql

import logging

logging.basicConfig(level=logging.INFO)  # ,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging = logging.getLogger(__name__)


class DataManager():
    def connect_db(self):
        return pymysql.connect(host='127.0.0.1',
                               port=3306,
                               user='root',
                               password='',
                               database='xinhua',
                               charset='utf8')


    def query_e2019(self,cc2,limit=''):
        sql_str = ("SELECT distinct(FILE_UUID),txt"
                   + " FROM e20190313"
                   + " WHERE txt like '%s' group by FILE_UUID,txt %s" % (cc2,'limit '+str(limit) if limit!='' else ''))
        logging.info(sql_str)

        con = self.connect_db()
        cur = con.cursor()
        cur.execute(sql_str)
        rows = cur.fetchall()
        cur.close()
        con.close()
        return rows

    def query_sql(self, sql_str):
        logging.info(sql_str)
        con = self.connect_db()
        cur = con.cursor()
        cur.execute(sql_str)
        rows = cur.fetchall()
        cur.close()
        con.close()
        return rows

# dm=DataManager()
# print(len(dm.query_e2019('%')))