# -*-coding:utf-8-*-
'''
消歧的实验

准备：
（1）政要名单数据：这部分已经全部保存到了aho_policical_person.aho中
（2）bert as server：用于将关键词向量化，需要启动成一个服务，现在模型用的是chinese_wwm_ext_L-12_H-768_A-12由哈工大改进版本
（3）ltp_server：用于文本词性标注，比较准确吧，需要下载编译。启动指令exe.sh中--segmentor-lexicon ltp_person.dict，是自定义词库
（4）place_dict.bin:地理位置对齐索引数据，之前的项目生成的，包含了地名的对齐，实体对应部分在place_index.bin中，原始数据\resources\regions.txt
（5）wordsense_detect.py:消歧，其中baidu_cache.bin用于缓存baidubaike数据抽取，word_dict.bin用于缓存词向量，这两部分可以不要，也可以用类似
redis来进行缓存
（6）flask.py：简单地服务化处理
（7）textProcess.py：一些jieba及其它文本处理的基础类，它的自定义词库./resources/all_dict_2.txt ./resources/stop.txt

大致思路：
（1）从文本中找到人名（词性）
（2）看是否是政要人名（对齐）
（3）抽取文本关键词（tf-idf,人名的定语，地理位置）
（4）向百度抽取所有同名人物基本数据，同时抽取各人数据的关键词
（5）词向量化（BERT）
（6）比较关键词向量相似性，并计算各组词向量相似性平均值得分
（7）得到得分最高的人物，看是否是库中政要人物

问题：
（1）有的政要人物有多个同名，也是政要人物（现在用索引保存了）
（2）有的政要不在政要库中（需要定期更新政要人物库，再跑准备程序）
（3）有的政要不在百度百科中，会出现误报（暂时没有处理方案）
（4）有的文本没有足够的背景信息（一方面想办法改进关键词加权，另一方面如果原始文本信息就少，则需要补充文本）
（5）百科政要数据不准确（头衔部分，可能需要根据近期新闻通过定中关系收集，再进行人工监督）
基本框架：
来源于https://huangyong.github.io的WordMultiSenseDisambiguation项目，改动了其中的向量化部分，关键词加权部分，附加了从上下文中抽取人名的部分
取消了同义场景分析（人名一般没有）
'''

import ahocorasick
import pickle
import pprint
import re

import requests
from dataManager import DataManager
from textProcess import TextProcess

import logging
from tqdm import tqdm

from wordsense_detect import MultiSenDetect

logging.basicConfig(level=logging.INFO)
logging = logging.getLogger(__name__)

class PersonDisambiguation():
    def __init__(self):
        self.tp=TextProcess()
        #数据库管理，加载政要数据
        self.dataManager=DataManager()
        # self.political_person_dict=list()
        #改用aho形式进行存储，方便进行多模匹配。
        self.aho_policical_person=ahocorasick.Automaton()
        try:
            # load_file = open('./mod/political_person_dict.bin', 'rb')
            # self.political_person_dict = pickle.load(load_file)
            # logging.info('political_person_dict count %d' % (len(self.political_person_dict)))
            file = open('./mod/aho_policical_person.aho', 'rb')
            self.aho_policical_person = pickle.load(file)
            logging.info('aho_policical_person count %d' % (len(self.aho_policical_person)))
        except:
            pass
        self.detector=MultiSenDetect()
        #加载地名数据索引，用于判断词性为hs的是否是地名
        load_file = open('./mod/place_dict.bin', 'rb')
        self.place_dict = pickle.load(load_file)
        logging.info('place_dict count %d' % (len(self.aho_policical_person)))
        return



    '''
    分辨政要人物，保存基本数据，生成政要人物对应百度数据字典
    '''
    def checkPersonBaike(self):
        rows=self.dataManager.query_sql("select * from psm_cityfather")
        persons=[]
        for row in rows:
            person=dict()
            person['id']=row[0]
            person['nationlity']=row[1]
            person['region']=row[2]
            person['cname']=row[3]
            person['duty']=row[7]
            persons.append(person)
        logging.info('persons count: %d' % len(persons))
        #使用消歧工具
        detector=MultiSenDetect()
        count=0
        persons_temp=self.political_person_dict
        bar=tqdm(persons)
        for person in bar:
            bar.set_description_str(person['cname'])
            # self.political_person_dict=list()
            for p in self.political_person_dict:
                if p['cname'] == person['cname'] and p['duty'] == person['duty']:
                    person['baikename'] = p['baikename']
                    person['baikeurl']=p['baikeurl']
                    person['baikeconcept']=p['baikeconcept']
                    person.update()
                    break
            if person.get('baikeconcept'):
                count = count + 1
                persons_temp.append(person)
                continue
            else:
                sent_embedding_res, wds_embedding_res=detector.detect_main(person['duty'],person['cname'])
                # print(sent_embedding_res)
                # print(wds_embedding_res)
                person['baikename']=wds_embedding_res[0][0]
                person['baikeurl']=detector.getConcept(person['baikename'])['link']
                person['baikeconcept']=detector.getConcept(person['baikename'])
                person.update()
                # pprint.pprint(person)

                count=count+1
                persons_temp.append(person)
            if count % 5==0:
                fou = open('./mod/political_person_dict.bin', 'wb')
                pickle.dump(persons_temp, fou)
                fou.close()
                detector.save_cache()
        detector.save_cache()
        fou = open('./mod/political_person_dict.bin', 'wb')
        pickle.dump(persons, fou)
        fou.close()

    # 服务器版的,完整化宾语，但下一句的后置宾语不能识别
    def complete_VOB_server(self, arcs,  word_index):

        word = arcs[word_index][1]
        prefix = ''
        postfix = ''
        for arc in arcs:
            if arc[5] == word_index and arc[2] < word_index:
                prefix += self.complete_VOB_server(arcs,  arc[2])
            if arc[5] == word_index and arc[2] > word_index:
                postfix += self.complete_VOB_server(arcs, arc[2])
        return prefix + word + postfix

    def findPerson(self,content):
        #1先分句
        sents=self.tp.cut_sentences(content)
        nrs=dict()
        geos=set()
        for sent in sents:
        #     nr=set(self.tp.posseg(sent,POS=['nr']))
        #     nrs=nrs.union(nr)
        # return nrs
            arcs=self.parseContent(sent)
            for arc in arcs:
                # 可能是人名了
                if arc[3]=='nh':
                    #从这里找到定中关键词，放进去
                    # nrs.add(arc[1])
                    prefix = ''
                    for arc_ in arcs:
                        if arc_[5] == arc[2] and arc_[2] < arc[2]:
                            prefix += self.complete_VOB_server(arcs, arc_[2])
                    # if prefix=='' :
                        # nrs[arc[1]] = [prefix]
                        # continue
                    pattern = r',|\.|/|;|\'|`|\[|\]|<|>|\?|:|"|\{|\}|\~|!|@|#|\$|%|\^|&|\(|\)|-|=|\_|\+|，|。|、|；|‘|’|【|】|·|！| |…|（|）'
                    prefix_list = re.split(pattern, prefix)
                    for prefix_ in prefix_list:
                        if nrs.get(arc[1]):
                            if prefix_ not in nrs.get(arc[1]) and prefix_!='':
                                nrs[arc[1]].append(prefix_)
                        else:
                            nrs[arc[1]]=[prefix_]
                if arc[3]=='ns':
                    if (self.place_dict.get(arc[1])):
                        geos.add(arc[1])

        return nrs,geos

    '''用LTP Server形成arcs和child_dict_list'''
    '''这部分可以有其它LTP工具代替'''
    def parser_main_ltpserver(self, sentence):
        url = 'http://192.168.1.101:8020/ltp'
        wb_data = requests.post(url, data={'s': sentence, 't': 'dp'}, json=True, allow_redirects=True)
        wb_data.encoding = 'utf-8'
        arcs_list = []
        try:
            content = wb_data.json()
            for c in content[0][0]:
                p = c.get('parent')
                pc = content[0][0][p]
                pname = pc.get('cont')
                ppos = pc.get('pos')
                arcs_list.append(
                    [c.get('relate'), c.get('cont'), c.get('id'), c.get('pos'), pname, c.get('parent'), ppos])

            child_dict_list = []
            for index in range(len(content[0][0])):
                child_dict = dict()
                for arc_index in range(len(arcs_list)):
                    # if arcs[arc_index].relation=='HED':
                    #     print('hed')
                    if arcs_list[arc_index][5] == index:  # arcs的索引从1开始---->把HED去掉了
                        if arcs_list[arc_index][0] in child_dict:
                            child_dict[arcs_list[arc_index][0]].append(arc_index)
                        else:
                            child_dict[arcs_list[arc_index][0]] = []
                            child_dict[arcs_list[arc_index][0]].append(arc_index)
                child_dict_list.append(child_dict)
        except:
            None
        return arcs_list, child_dict_list

    def parseContent(self,sent):
        arcs, child_dict_list = self.parser_main_ltpserver(sent)
        return arcs

    def test1(self):
        load_file = open('./mod/political_person_dict.bin', 'rb')
        political_person_dict = pickle.load(load_file)
        # pprint.pprint(political_person_dict)
        for i, person in enumerate(political_person_dict):
            if person['cname']=='哈勒特马·巴特图勒嘎':
                pprint.pprint(person)
                pprint.pprint(i)
                break
    '''
    更新political_person_dict的数据，而不全重新生成
    '''
    def update_political_person_dict(self,cname,duty):
        load_file = open('./mod/political_person_dict.bin', 'rb')
        political_person_dict = pickle.load(load_file)
        for i, person in enumerate(political_person_dict):
            if person['cname']==cname and person['duty']==duty:
                sent_embedding_res, wds_embedding_res = self.detector.detect_main(person['duty'], person['cname'],person['duty'])
                # print(sent_embedding_res)
                # print(wds_embedding_res)
                person['baikename'] = wds_embedding_res[0][0]
                person['baikeurl'] = self.detector.getConcept(person['baikename'])['link']
                person['baikeconcept'] = self.detector.getConcept(person['baikename'])
                person.update()
                pprint.pprint(person)
        fou = open('./mod/political_person_dict.bin', 'wb')
        pickle.dump(political_person_dict, fou)
        fou.close()

    '''
    利用百分点服务，得到同义词，用于对齐
    '''
    def get_sim(self, something):
        url = 'http://10.122.141.12:9006/similar'
        r = requests.post(url, json={"ck": "synonym", "synonym_word": something, "synonym_selectedMode": "auto",
                                          "homoionym_word": "", "homoionym_selectedMode": "auto", "homoionym_num": ""})
        json = r.json()
        result = json['detail']['res']['synonym']
        return result

    '''
    生成模匹配索引，也可以用dict来代替，
    实际没有真正用模式匹配来取得人名，而是用LTP词性识别来做的，这样准确度比较好。
    '''
    def genAhocorasick(self):
        load_file = open('./mod/political_person_dict.bin', 'rb')
        self.political_person_dict = pickle.load(load_file)
        self.aho_policical_person=ahocorasick.Automaton()
        for i,person in enumerate(self.political_person_dict):
            word=person.get('cname')
            #这里发现要有外国人名对齐功能，唐纳德·特朗普===》特朗普、川普   习近平---》习主席，
            #但大部分中国人名，不需要对齐，
            aliasPerson = self.get_sim(word)
            baidualias=person.get('baikeconcept').get('别名')
            if word.find('·')>-1:
                aliasPerson.append(word[word.index('·')+1:])
                aliasPerson.append(word[word.rindex('·')+1:])
                #去掉中间名
                aliasPerson.append(word[word.index('·') + 1:]+word[word.rindex('·'):])

            baidualias_list=[]
            if baidualias:
                pattern = r',|\.|/|;|\'|`|\[|\]|<|>|\?|:|"|\{|\}|\~|!|@|#|\$|%|\^|&|\(|\)|-|=|\_|\+|，|。|、|；|‘|’|【|】|·|！| |…|（|）'
                baidualias_list = re.split(pattern, baidualias)
            person_all = set([word]).union(set(aliasPerson)).union(set(baidualias_list))
            for word_ in person_all:
                persons=[]
                if self.aho_policical_person.exists(word_):
                    persons=self.aho_policical_person.get(word_)
                persons.append(person)
                self.aho_policical_person.add_word(word_,persons)
        self.aho_policical_person.make_automaton()
        # s=self.aho_policical_person.get('习近平')
        # pprint.pprint(s)
        out=open('./mod/aho_policical_person.aho','wb')
        out.write(pickle.dumps(self.aho_policical_person))
        out.close()

    def testAho(self):
        sent='本院受理的原告易纲诉被告吴勇、王国珍机动车交通事故责任纠纷一案，现已审理终结。判决如下：一、自本判决生效之日起三日内，王国珍赔偿杨旭维修费11703元；二、驳回杨旭的其他诉讼请求。因你下落不明，现依法向你公告送达本案的民事判决书。自本公告发出之日起，经过60日即视为送达。如不服本判决，可在判决书送达之日起十五日内，向本院递交上诉状，并按对方当事人的人数提出副本，上诉于广州市中级人民法院。特此公告。'
        file=open('./mod/aho_policical_person.aho','rb')
        aho_policical_person=pickle.load(file)
        for word in aho_policical_person.iter('刘惠'):
            pprint.pprint(word)
    '''
    识别文本中的政要人物
    repeat:是否要对每一个名字（即使文章中多次出现）进行识别
    att_weight:是否要进行人物头衔的加权
    geo_weight:是否要进行地理位置的加权
    '''
    def recongnizePoliticalPerson(self,sent,repeat=False,att_weight=True,geo_weight=True):
        pperon_candidates=[]
        pperson_sure=[]
        npperson_sure=[]
        #一句话中也可能有多个政要人名，多个重名怎么办，这种模式下会对有重复字的名字进行抽取
        # 如果有两个字的政要，恰好有三个字的其它人员，则会出现误判，所以最合理的
        # 方式仍然是利用分词和句法分析来定中分析。
        # 要先进行词法分析才行，这里用了LTP的server来做的，jieba的不准确，需要启动ltp_server
        nrs,geos=self.findPerson(sent)
        # for word in self.aho_policical_person.iter(sent):
        for nr in nrs:
            if not self.aho_policical_person.exists(nr):#只处理政要名字，以及与政要重名的名字，其它人名不处理
               continue
            ppersons=self.aho_policical_person.get(nr)#此处已包括重名政要，但不包括非政要

            #一句话里出现多次名字，只取一次，提高效率
            flag=True
            if not repeat:
                for pperon_candidate in pperon_candidates:
                    if pperon_candidate.get('cname')==ppersons[0].get('cname'):
                        flag=False
            if not flag: continue
            pperon_candidates=pperon_candidates+ppersons
            #把定中的关键词加权给到判断过程中
            att = []
            if att_weight:
                att = nrs.get(nr)
            #地理位置加权
            geo=[]
            if geo_weight:
                # geo=self.geoKG.parseDoc_global(sent)
                geo=geos
            # sent_embedding_res暂时无用，顺接原来的接口，
            sent_embedding_res, wds_embedding_res = self.detector.detect_main(sent, ppersons[0].get('cname'), att, geo)
            concept=self.detector.getConcept(wds_embedding_res[0][0])#拿回元数据
            for pperson in ppersons:
                #政治人物 是百度给人物打的标签，这里为加强准确性，判断是否符合标签
                if concept.get('出生日期')==pperson.get('baikeconcept').get('出生日期') and '政治人物' in concept.get('tags'):
                    pprint.pprint(pperson)
                    pperson_sure.append(pperson)
                    break
            if len(pperson_sure)==0:
                    concept['是否政要']='否'
                    pprint.pprint(concept)
                    npperson_sure.append(concept)
        #保存baidu的访问缓存
        self.detector.save_cache()
        return pperson_sure,npperson_sure


if __name__ == '__main__':
    pd=PersonDisambiguation()
    # pd.genAhocorasick()
    # pd.testAho()
    # pd.checkPersonBaike()
    # pd.test1()
    sent='8月11日，区委书记刘惠接待中铁十六局集团有限公司程红彬一行到我区考察交流。双方召开座谈会，与会人员观看了中铁十六局集团和津南区宣传片，随后双方围绕高标准推进区域规划开发、高质量推进项目建设、高水平推进政企合作等方面进行深入交流。'
    sent='8月9日上午，省纪委监委召开“不忘初心、牢记使命”主题教育先进事迹报告会。省委常委、省纪委书记、省监委主任刘惠出席，省委第一巡回指导组到会指导。'
    # sent='刘惠 ，男，我国著名相声演员，师承相声表演艺术家姜昆老师。刘惠于2005年涉足影视，在电视剧《家家有本难念的经》里，他扮演了一个有七八集戏份的角色。'
    # sent='市委书记李强上午来到上海展览中心参观上海书展，与市民群众一起感受浓厚书香氛围。李强指出，要坚持以习近平新时代中国特色社会主义思想为指导，围绕举旗帜、聚民心、育新人、兴文化、展形象的使命任务，充分发挥上海书展促进全民阅读、增强文化底蕴的重要作用，不断提升吸引力、影响力，推动多出好书、多出精品，营造更加浓厚的书香社会氛围，为打响“上海文化”品牌、加快建设国际文化大都市作出更大贡献。'
    # sent='中国环境报记者张铭贤 通讯员郭运洲石家庄报道 河北省石家庄市日前召开生态环境保护委员会暨大气污染防治工作领导小组会议。河北省委常委、石家庄市委书记邢国辉主持会议并讲话。'
    # sent='6月12日晚，湖南省政府办公厅(研究室、政务局)召开“不忘初心、牢记使命”主题教育工作会议，省政府党组成员、秘书长，办公厅党组书记王群出席并作动员讲话。'
    # sent='美国总统特朗普在周日宣称，他将会向台湾销售f-16v战斗机，这一笔军售数量很大，请问中方对此有何评论'
    # sent='印度国防部长辛格当天提到了“核武器”,这位莫迪的爱将说,“印度遵守‘不首先使用核武器’的政策'
    # sent='交部发言人耿爽宣布:应哥伦比亚政府邀请,国家主席习近平特使、交通运输部部长李小鹏将赴波哥大出席活动'
    # sent='克维里卡什维利'
    # sent='最高检党组书记、检察长张军强调,检察机关领导干部要以上率下,加强党的政治建设,落实管党治党责任,确保主题教育见实效、收长效。'
    pprint.pprint(sent)
    # pd.update_political_person_dict('唐纳德·特朗普','总统')
    pd.recongnizePoliticalPerson(sent)