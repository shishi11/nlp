import codecs

from textProcess import TextProcess
import logging

import pymysql

def genTxt():
    rows=query('%习近平%')
    textProcess=TextProcess()
    allcent = list()
    for row in rows:

        title = row[3]
        content = row[4]
        #这里应该按符号进行分隔，分成句，不要符号
        temp=textProcess.cut_sent(title,',')+textProcess.cut_sent(content,',')
        print(temp)

        allcent.extend([item for item in temp if len(item)>9])
        allcent.extend(['\n'])
    fou=open('./resources/bert_pretrain.txt', 'w', encoding='UTF-8')
    for row in allcent:
        words=textProcess.cut(row)
        if(row!='\n'):
            fou.write(' '.join(list(words))+'\n')
        else:
            fou.write('\n')
    fou.close()
    return
def connect_db():
    return pymysql.connect(host='127.0.0.1',
                           port=3306,
                           user='root',
                           password='',
                           database='xinhua',
                           charset='utf8')


def query(cc2):
    sql_str = ("SELECT *"
               + " FROM news_"
               + " WHERE detail like '%s' limit 10" %  cc2)
    logging.info(sql_str)

    con = connect_db()
    cur = con.cursor()
    cur.execute(sql_str)
    rows = cur.fetchall()
    cur.close()
    con.close()

    # assert len(rows) == 1, 'Fatal error: country_code does not exists!'
    return rows

def genVocab():
    word_freq=load_word_freq_dict('./resources/all_dict_2.txt')
    fou=open('./resources/bert_vocab.txt', 'w', encoding='UTF-8')
    for word in word_freq:
        fou.write(word+'\n')
    fou.write('[PAD]'+'\n')
    fou.write('[UNK]'+'\n')
    fou.write('[CLS]' + '\n')
    fou.write('[SEP]' + '\n')
    fou.write('[MASK]' + '\n')
    fou.close()
    return

def load_word_freq_dict(path):
        """
        加载切词词典
        :param path:
        :return:
        """
        word_freq = {}

        with codecs.open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#'):
                    continue
                info = line.split()
                if len(info) < 1:
                    continue
                word = info[0]
                # self.aho_word.add_word(word, word)
                # 取词频，默认1
                try:
                    freq = int(info[1]) if len(info) > 1 else 1
                except:
                    freq=1
                word_freq[word] = freq
        return word_freq

if __name__ == '__main__':
    # genVocab()
    genTxt()