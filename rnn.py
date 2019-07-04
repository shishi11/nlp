import _sqlite3

from textgenrnn import textgenrnn

import textProcess


def readNews():
    conn=_sqlite3.connect('./resources/news0712.db')
    cursor=conn.cursor()
    news=cursor.execute("select * from news where title like '%习近平%'")
    news=[c for c in news]
    conn.close()
    return news

def genRnnTrainText():
    news = readNews()
    fou = open('./resources/xjpnews_rnn_corpus.txt', 'w', encoding='utf-8')
    textProcess.TextProcess()
    for news_ in news[:1000]:
        text=news_[3]+' '+news_[4]
        t1=textProcess.TextProcess.doAll(text,dst=False)
        fou.write(t1+ "\n")
    fou.close()
def gen():
    # textgen=textgenrnn(name='cnn4')
    textgen=textgenrnn(weights_path='./cnn4_weights.hdf5',config_path='./cnn4_config.json',
      vocab_path='./cnn4_vocab.json')
    # textgen.reset()                                         # 重置模型
    textgen.train_from_file(                                # 从数据文件训练模型
        file_path = './resources/xjpnews_rnn_corpus.txt',  # 文件路径
        new_model = False,                                   # 训练新模型
        num_epochs = 2,                                    # 训练轮数

        # word_level = True,                                 # True:词级别，False:字级别
        rnn_bidirectional = True,                           # 是否使用Bi-LSTM
        # max_length = 25,                                    # 一条数据的最大长度
        # weights_path='./mod/cnn4_weights.hdf5',
        # config_path='./mod/cnn4_config.json',
        # vocab_path='./mod/cnn4_vocab.json'
    )
    textgen.save(
        weights_path='./cnn4_weights.hdf5'
    )

    textgen.generate(1)

def genText():
    textgen=textgenrnn(weights_path='./cnn4_weights.hdf5',config_path='./cnn4_config.json',
      vocab_path='./cnn4_vocab.json')
    text=textgen.generate(1)
    news = readNews()
    texts=[]
    for news_ in news[:1000]:
        text=news_[3]+' '+news_[4]
        texts.append(text)
    r=textgen.similarity(text[0],texts)
    print(r)

if __name__=='__main__':
    # genRnnTrainText()
    gen()
    # genText()