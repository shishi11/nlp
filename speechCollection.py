'''
1.用SQL语句找到包含人特的文章
2.分句
3.找到人特句，和动词
'''
import os
import pickle
import re
import requests
from pyltp import Segmentor, Postagger, Parser, NamedEntityRecognizer, SementicRoleLabeller

import pymysql
import logging

import zhon.hanzi
from collections import defaultdict

from aip import nlp

from TimeNormalizer import TimeNormalizer
from data.db_util import NeoManager
from global_person_test import PersonKG


class BaiduNLP():

    def __init__(self):
        APP_ID = '11235055'
        API_KEY = 'bV6xo4QkDRPFy0Ux86Vik6H9'
        SECRET_KEY = 'CrrBHbVZOzXK32XrzGXaP7Ggl5VtM0E2'
        self.client = nlp.AipNlp(APP_ID, API_KEY, SECRET_KEY)


class LtpParser():
    last_sent_people = None
    last_people = None

    def connect_wxremit_db(self):
        return pymysql.connect(host='127.0.0.1',
                               port=3306,
                               user='root',
                               password='',
                               database='xinhua',
                               charset='utf8')

    def query_country_name(self, cc2):
        sql_str = ("SELECT distinct(FILE_UUID),txt"
                   + " FROM e20190315"
                   + " WHERE txt like '%s' group by FILE_UUID,txt limit 25,1 " % cc2)
        logging.info(sql_str)

        con = self.connect_wxremit_db()
        cur = con.cursor()
        cur.execute(sql_str)
        rows = cur.fetchall()
        cur.close()
        con.close()

        # assert len(rows) == 1, 'Fatal error: country_code does not exists!'
        return rows

    '''移除括号内的信息，去除噪声'''

    def remove_noisy(self, content):
        p1 = re.compile(r'（[^）]*）')
        p2 = re.compile(r'\([^\)]*\)')
        return p2.sub('', p1.sub('', content))

    def __init__(self):
        self.out = open('./resources/result.txt', 'w', encoding='UTF-8')
        import pyltp
        self.splitter = pyltp.SentenceSplitter()

        LTP_DIR = "./ltp_data_v3.4.0"
        self.segmentor = Segmentor()
        self.segmentor.load_with_lexicon(os.path.join(LTP_DIR, "cws.model"), './resources/ltp_person.dict')
        self.segmentor.load(os.path.join(LTP_DIR, "cws.model"))

        self.postagger = Postagger()
        self.postagger.load_with_lexicon(os.path.join(LTP_DIR, "pos.model"), './resources/ltp_person.dict')
        self.postagger.load(os.path.join(LTP_DIR, "pos.model"))

        self.baidu = BaiduNLP()
        self.speechV = ['表示', '暗示', '告诉', '说', '称', '宣布', '声称', '希望', '指出', '强调', '声明', '宣称', '警告', '发表','认为','显示','介绍','认定','分析']
        self.neoManager = NeoManager()

    def init(self):
        import pyltp
        # self.splitter=pyltp.SentenceSplitter()

        LTP_DIR = "./ltp_data_v3.4.0"
        # self.segmentor = Segmentor()
        # self.segmentor.load_with_lexicon(os.path.join(LTP_DIR, "cws.model"),'./resources/ltp_dict.txt')
        #
        # self.postagger = Postagger()
        # self.postagger.load_with_lexicon(os.path.join(LTP_DIR, "pos.model"),'./resources/ltp_dict.txt')

        self.parser = Parser()
        self.parser.load(os.path.join(LTP_DIR, "parser.model"))

        self.recognizer = NamedEntityRecognizer()
        # self.recognizer.load(os.path.join(LTP_DIR, "ner.model"))

        self.labeller = SementicRoleLabeller()

        self.labeller.load(os.path.join(LTP_DIR, 'pisrl.model'))

    def release(self):
        # self.segmentor.release()
        # self.postagger.release()
        self.parser.release()
        self.labeller.release()

    '''ltp基本操作'''

    def basic_parser(self, words):
        postags = list(self.postagger.postag(words))
        netags = self.recognizer.recognize(words, postags)
        return postags, netags

    '''ltp获取词性'''

    def get_postag(self, words):
        return list(self.postagger.postag(words))

    '''基于实体识别结果,整理输出实体列表'''

    def format_entity(self, words, netags, postags):
        name_entity_dist = {}
        name_entity_list = []
        place_entity_list = []
        organization_entity_list = []
        ntag_E_Nh = ""
        ntag_E_Ni = ""
        ntag_E_Ns = ""
        index = 0
        for item in zip(words, netags):
            word = item[0]
            ntag = item[1]
            if ntag[0] != "O":
                if ntag[0] == "S":
                    if ntag[-2:] == "Nh":
                        name_entity_list.append(word + '_%s ' % index)
                    elif ntag[-2:] == "Ni":
                        organization_entity_list.append(word + '_%s ' % index)
                    else:
                        place_entity_list.append(word + '_%s ' % index)
                elif ntag[0] == "B":
                    if ntag[-2:] == "Nh":
                        ntag_E_Nh = ntag_E_Nh + word + '_%s ' % index
                    elif ntag[-2:] == "Ni":
                        ntag_E_Ni = ntag_E_Ni + word + '_%s ' % index
                    else:
                        ntag_E_Ns = ntag_E_Ns + word + '_%s ' % index
                elif ntag[0] == "I":
                    if ntag[-2:] == "Nh":
                        ntag_E_Nh = ntag_E_Nh + word + '_%s ' % index
                    elif ntag[-2:] == "Ni":
                        ntag_E_Ni = ntag_E_Ni + word + '_%s ' % index
                    else:
                        ntag_E_Ns = ntag_E_Ns + word + '_%s ' % index
                else:
                    if ntag[-2:] == "Nh":
                        ntag_E_Nh = ntag_E_Nh + word + '_%s ' % index
                        name_entity_list.append(ntag_E_Nh)
                        ntag_E_Nh = ""
                    elif ntag[-2:] == "Ni":
                        ntag_E_Ni = ntag_E_Ni + word + '_%s ' % index
                        organization_entity_list.append(ntag_E_Ni)
                        ntag_E_Ni = ""
                    else:
                        ntag_E_Ns = ntag_E_Ns + word + '_%s ' % index
                        place_entity_list.append(ntag_E_Ns)
                        ntag_E_Ns = ""
            index += 1
        name_entity_dist['nhs'] = self.modify_entity(name_entity_list, words, postags, 'nh')
        name_entity_dist['nis'] = self.modify_entity(organization_entity_list, words, postags, 'ni')
        name_entity_dist['nss'] = self.modify_entity(place_entity_list, words, postags, 'ns')
        return name_entity_dist

    '''entity修正,为rebuild_wordspostags做准备'''

    def modify_entity(self, entity_list, words, postags, tag):
        entity_modify = []
        if entity_list:
            for entity in entity_list:
                entity_dict = {}
                subs = entity.split(' ')[:-1]
                start_index = subs[0].split('_')[1]
                end_index = subs[-1].split('_')[1]
                entity_dict['stat_index'] = start_index
                entity_dict['end_index'] = end_index
                if start_index == entity_dict['end_index']:
                    consist = [words[int(start_index)] + '/' + postags[int(start_index)]]
                else:
                    consist = [words[index] + '/' + postags[index] for index in
                               range(int(start_index), int(end_index) + 1)]
                entity_dict['consist'] = consist
                entity_dict['name'] = ''.join(tmp.split('_')[0] for tmp in subs) + '/' + tag
                entity_modify.append(entity_dict)
        return entity_modify

    '''基于命名实体识别,修正words,postags'''

    def rebuild_wordspostags(self, name_entity_dist, words, postags):
        pre = ' '.join([item[0] + '/' + item[1] for item in zip(words, postags)])
        post = pre
        for et, infos in name_entity_dist.items():
            if infos:
                for info in infos:
                    post = post.replace(' '.join(info['consist']), info['name'])
        post = [word for word in post.split(' ') if len(word.split('/')) == 2 and word.split('/')[0]]
        words = [tmp.split('/')[0] for tmp in post]
        postags = [tmp.split('/')[1] for tmp in post]

        return words, postags

    '''依存关系格式化'''

    def syntax_parser(self, words, postags):
        arcs = self.parser.parse(words, postags)
        words = ['Root'] + words
        postags = ['w'] + postags
        tuples = list()
        for index in range(len(words) - 1):
            arc_index = arcs[index].head
            arc_relation = arcs[index].relation
            tuples.append(
                [index + 1, words[index + 1], postags[index + 1], words[arc_index], postags[arc_index], arc_index,
                 arc_relation])

        return tuples

    '''为句子中的每个词语维护一个保存句法依存儿子节点的字典'''
    # def build_parse_child_dict(self, words, postags, tuples):
    #     child_dict_list = list()
    #     for index, word in enumerate(words):
    #         child_dict = dict()
    #         for arc in tuples:
    #             if arc[3] == word:
    #                 if arc[-1] in child_dict:
    #                     child_dict[arc[-1]].append(arc)
    #                 else:
    #                     child_dict[arc[-1]] = []
    #                     child_dict[arc[-1]].append(arc)
    #         child_dict_list.append([word, postags[index], index, child_dict])
    #
    #     return child_dict_list

    '''句法分析---为句子中的每个词语维护一个保存句法依存儿子节点的字典'''

    def build_parse_child_dict(self, words, postags, arcs):
        child_dict_list = []
        format_parse_list = []
        for index in range(len(words)):
            child_dict = dict()
            for arc_index in range(len(arcs)):
                # if arcs[arc_index].relation=='HED':
                #     print('hed')
                if arcs[arc_index].head == index + 1:  # arcs的索引从1开始---->把HED去掉了
                    if arcs[arc_index].relation in child_dict:
                        child_dict[arcs[arc_index].relation].append(arc_index)
                    else:
                        child_dict[arcs[arc_index].relation] = []
                        child_dict[arcs[arc_index].relation].append(arc_index)
            child_dict_list.append(child_dict)
        rely_id = [arc.head for arc in arcs]  # 提取依存父节点id
        relation = [arc.relation for arc in arcs]  # 提取依存关系
        heads = ['Root' if id == 0 else words[id - 1] for id in rely_id]  # 匹配依存父节点词语
        for i in range(len(words)):
            # ['ATT', '李克强', 0, 'nh', '总理', 1, 'n']
            a = [relation[i], words[i], i, postags[i], heads[i], rely_id[i] - 1, postags[rely_id[i] - 1]]
            format_parse_list.append(a)

        return child_dict_list, format_parse_list

    '''parser主函数'''

    # def parser_main(self, words, postags):
    #     tuples = self.syntax_parser(words, postags)
    #     child_dict_list = self.build_parse_child_dict(words, postags, tuples)
    #     return tuples, child_dict_list

    def parser_main(self, sentence):

        words = list(self.segmentor.segment(sentence))
        postags = list(self.postagger.postag(words))
        arcs = self.parser.parse(words, postags)
        child_dict_list, format_parse_list = self.build_parse_child_dict(words, postags, arcs)
        roles_dict = self.format_labelrole(words, postags)
        return words, postags, child_dict_list, roles_dict, format_parse_list

    def parser_main1(self, sentence):

        words = list(self.segmentor.segment(sentence))
        postags = list(self.postagger.postag(words))
        arcs = self.parser.parse(words, postags)
        child_dict_list, format_parse_list = self.build_parse_child_dict(words, postags, arcs)
        # roles_dict = self.format_labelrole(words, postags)
        return format_parse_list

    # 利用LTP 服务器进行处理，本地崩的可能性大一些，他自己有一个run.pl的脚本，可以改成守护进程
    def parser_main_ltpserver(self, sentence):
        url = 'http://127.0.0.1:8020/ltp'
        wb_data = requests.post(url, data={'s': sentence, 't': 'dp'}, json=True, allow_redirects=True)
        wb_data.encoding = 'utf-8'
        arcs_list = []
        try:
            content = wb_data.json()
            # words = list(self.segmentor.segment(sentence))
            # postags = list(self.postagger.postag(words))
            # arcs = self.parser.parse(words, postags)
            # child_dict_list, format_parse_list = self.build_parse_child_dict(words, postags, arcs)
            # roles_dict = self.format_labelrole(words, postags)

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
        # [[c.get('relate'),c.get['cont'],c.get('id'),c.get('pos'),c.get('parent'),c.get('parent')] for c in content[0][0]]
        # return format_parse_list
        return arcs_list, child_dict_list

    '''利用百度处理'''

    def parser_main_baidu(self, sentence):
        try:
            arcs = self.baidu.client.depParser(sentence)
        except:
            arcs = {"items": []}
        return arcs.get("items")

    '''基础语言分析'''

    def basic_process(self, sentence):
        words = list(self.segmentor.segment(sentence))
        postags, netags = self.basic_parser(words)
        name_entity_dist = self.format_entity(words, netags, postags)
        words, postags = self.rebuild_wordspostags(name_entity_dist, words, postags)
        return words, postags

    '''语义角色标注'''

    def format_labelrole(self, words, postags):
        arcs = self.parser.parse(words, postags)
        roles = self.labeller.label(words, postags, arcs)
        roles_dict = {}
        for role in roles:
            roles_dict[role.index] = {arg.name: [arg.name, arg.range.start, arg.range.end] for arg in role.arguments}
        return roles_dict

    '''收集命名实体'''

    def collect_ners(self, words, postags):
        ners = []
        for index, pos in enumerate(postags):
            if pos in self.ners:
                ners.append(words[index] + '/' + pos)
        return ners

    '''对文章进行分句处理'''

    def seg_content(self, content):
        # return [sentence for sentence in re.split(r'[？?！!。；;：:\n\r]', content) if sentence]
        return list(self.splitter.split(content))

    '''
    抽取出事件三元组
    '''

    def extract_triples(self, words, postags):
        svo = []
        tuples, child_dict_list = self.parser_main(words, postags)
        for tuple in tuples:
            rel = tuple[-1]
            if rel in ['SBV']:
                sub_wd = tuple[1]
                verb_wd = tuple[3]
                obj = self.complete_VOB(verb_wd, child_dict_list)
                subj = sub_wd
                verb = verb_wd
                if not obj:
                    svo.append([subj, verb])
                else:
                    svo.append([subj, verb + obj])
        return svo

    '''根据SBV找VOB'''

    # def complete_VOB(self, verb, child_dict_list):
    #     for child in child_dict_list:
    #         wd = child[0]
    #         attr = child[3]
    #         if wd == verb:
    #             if 'VOB' not in attr:
    #                 continue
    #             vob = attr['VOB'][0]
    #             obj = vob[1]
    #             return obj
    #     return ''

    def get_people(self, words, postags, child_dict_list, word_index):
        if postags[word_index] == 'nh':
            return word_index
        child_dict = child_dict_list[word_index]
        for relation in child_dict:
            if 'ATT' == relation:
                for index in child_dict[relation]:
                    # people=self.get_people(words,postags,child_dict_list,index)
                    if postags[index] == 'nh': return index
                    # if people: return people
                # return self.get_people(words,postags,child_dict_list,child_dict[relation])
        return None

    def get_peoples(self, words, postags, child_dict_list, word_index):
        indexes = []
        if postags[word_index] in ['nh', 'r']:
            indexes.append(word_index)

        child_dict = child_dict_list[word_index]
        for relation in child_dict:
            if 'ATT' == relation:
                for index in child_dict[relation]:
                    # people=self.get_people(words,postags,child_dict_list,index)
                    if postags[index] == 'nh':  # 习近平总书记
                        indexes.append(index)
                        child_dict_ = child_dict_list[index]

                        if 'COO' in child_dict_:
                            for coo in child_dict_['COO']:
                                if postags[coo] == 'nh':
                                    indexes.append(coo)
                    # if people: return people
                # return self.get_people(words,postags,child_dict_list,child_dict[relation])
            if 'COO' == relation:  # 出现平行关系
                for index in child_dict[relation]:
                    if postags[index] == 'nh':
                        indexes.append(index)
                    child_dict1 = child_dict_list[index]
                    for relation1 in child_dict1:
                        if 'ATT' == relation:
                            for index1 in child_dict1[relation]:
                                # people=self.get_people(words,postags,child_dict_list,index)
                                if postags[index1] == 'nh':  # 习近平总书记
                                    indexes.append(index1)
        if (self.lookforpeoples):
            indexes = [index for index in indexes if words[index] in self.lookforpeoples]
        return indexes

    def trans_pronoun(self, word, postags, p):
        if word in ['他', '她']:
            if self.last_people:
                return self.last_people
            elif self.last_sent_people:
                return self.last_sent_people
            else:
                return word
        if postags[p] == 'nh': return word
        return None

    # def find_title_coo(self,arcs,word_index,title,place,ttuple):
    #     None
    def find_title_baidu(self, arcs, word_index, title, place, ttuple, person):
        for arc in arcs:
            if (arc.get("head") == word_index and arc.get('deprel') != 'COO'):
                title, place, ttuple = self.find_title_baidu(arcs, arc.get("id"), title, place, ttuple, person)
                if (arc.get("postag") != 'ns'):
                    title += arc.get("word")
                if arc.get("postag") == 'ns':
                    # ns要进行归一化对齐
                    place += arc.get("word")

            if (arc.get('head') == word_index and arc.get('deprel') == 'COO'):
                title_, place_, ttuple = self.find_title_baidu(arcs, arc.get('id'), '', '', ttuple, person)
                if arc.get('head') not in [a.get('id') for a in arcs if a.get('deprel') == 'COO']:
                    if (arc.get("postag") != 'ns'):
                        title_ += arc.get("word")
                    if arc.get("postag") == 'ns':
                        place_ += arc.get("word")
                    # print(title_,place_)

                    ttuple[person].append((title_, place_))
        return title, place, ttuple

    def find_place(self,arcs,word_index,place=None):

        for arc in arcs:#对于  美国休斯顿 这样的多级地名，怎么处理
            if arc[5]==word_index :#and arc[0]=='ATT':
                if arc[3]=='ns' or self.place_dict.get(arc[1]) and len(arc[1])>1:
                    temp = self.place_dict.get(arc[1])
                    if place and temp:temp.append(place)
                    #这里多义
                    if(temp and len(temp)>1 and place):
                        place_dict=place
                        level=place_dict['level']
                        for item in temp:
                            item_dict = self.place_index.get(item['id'])
                            pitem_dict = self.place_index.get(item['pid'])
                            while pitem_dict['level']>level:
                                pitem_dict=self.place_index.get(pitem_dict['pid'])
                            if pitem_dict==place_dict:
                                place=pitem_dict
                                place['id']=pitem_dict['id']
                                break


                        # None
                    else:
                        if temp :
                            #排下充nts1.sort(key=lambda it:it[0])
                            temp_=temp[0]
                            for p in temp:
                                if int(p['pid'])<int(temp_['pid']):
                                    temp_=p
                            place=self.place_index.get(temp_['id'])
                            place['id']=temp_['id']
                        else:
                            place=None
                place_=self.find_place(arcs,arc[2],place)#这个模式下，找到最小的那个地理位置
                if place_:
                    place=place_

        return place


    def ruler_speech(self, arcs, child_dict_list,sent):
        ttuple = defaultdict(list)
        stuple = defaultdict(list)
        otuple = defaultdict(list)

        for arc in arcs:
            if arc[6] == 'nh' and arc[2] not in [a[2] for a in arcs if a[0] == 'ATT' and a[2] == arc[5]]:
                person = arc[4]
                if len(person.strip())<=1:continue #这里应该进行实体对齐

                #应对外国名字长短变化 A-B ---> B
                # for pname in ttuple:---->还没有全局化
                #     if pname.find(person)>-1:
                #         person=pname
                #         break
                if (arc[0] == 'ATT' and arc[3] in ['n','r']):
                    # 这是第一个定语词
                    word_index = arc[5]
                    #其实只要最小的，再往上的由地理库直接支持总结
                    # title, place, ttuple = self.find_title(arcs, word_index, '', '', ttuple, person)
                    ttuple=self.find_title1(arcs, word_index, ttuple, person)
                    # place=self.find_place(arcs, word_index)
                    # if (title or place):
                    #     ttuple[person].append((title, place))

        for arc in arcs:
            # 可能有双动词情况，xxx写信表示，这时写与表示是COO ，第一HED可能是写，这个还没有处理好
            #if arc[1] in self.speechV:  # 先找动词（观点动词）
                if (arc[0] == 'HED'  ) and arc[3] == 'v':  # 简化一点，就不向前找HED了，认为可用
                    # print(arc)
                    # SBV_ADV_POB  --->乔布斯在斯坦福大学演讲。
                    # SBV_CMP_POB  ---># 哈德森出身在伦敦。
                    # SBV_VOB     ---->特朗普是美国总统。---->主谓+动宾
                    # FOB_ADV_POB ----># 孟晚舟被拘留。
                    speechV_ids=[]
                    if arc[1] in self.speechV:
                        speechV_ids=[arc[2]]
                    for arc_ in arcs:
                        if arc_[0]=='COO' and arc_[3] == 'v' and (arc_[5] in speechV_ids  or (arc_[5]==arc[2] and arc_[1] in self.speechV)):
                            if arc[2] not in speechV_ids:
                                speechV_ids.insert(0,arc[2])
                            speechV_ids.append(arc_[2])

                    subject = None
                    for arc_ in arcs:
                        # 前面要找到人名或机构名
                        # 也少COO 的部分== arc[2]
                        if (arc_[0] == 'SBV' and arc_[5] == arc[2]  and arc_[3] not in ['v','wp'] and len(speechV_ids)>0):
                                # or arc_[0] == 'SBV' and arc_[5] ==:

                            title, place, xtuple = self.find_title_server(arcs, arc_[2])

                            if ttuple.get(arc_[1])==None:
                                xtuple = self.find_title1(arcs, arc_[2], defaultdict(list), arc_[1])

                                subject=xtuple[arc_[1]][0][0]+arc_[1] if len(xtuple)>0 else arc_[1]
                                # if title==None:title=''
                                # if place==None:place=''
                                # if title!='' and place!='' and title.find(place)>-1 :
                                #     subject = title + arc_[1]
                                # else:
                                #     #这里有一种情况要处理称谓，习主席，习近平同志，李克强总理，不然只能后融合时再处理了
                                #     subject = place+title+arc_[1]
                            else:
                                subject=arc_[1]
                            subject=subject.strip()
                            if len(subject)==0:continue

                            if (ttuple.get(arc_[1]) == None):
                                #不是人名
                                place=self.find_place(arcs,arc_[2])
                                if place:
                                    otuple[subject].append((title,place))
                                # for pname in ttuple:----》还没有全局化
                                #     if pname.find(arc_[1]) > -1:
                                #         subject = pname
                                #         break
                                if self.last_people!='' and self.last_people.find(arc_[1]) > -1:
                                    subject = self.last_people
                            #这里可能是类似 华盛顿宣布 XXX
                            if subject in ['他','她','我']:
                                if self.last_people:
                                    subject=self.last_people
                            speech = None
                            speechV=arc[1]
                            for arc_1 in arcs:
                                # 后面补言论内容
                                # if arc_1[5] in  speechV_ids and arc_1[3] not in ['wp'] and arc_1[0] != 'SBV':
                                if (arc_1[0] in ['VOB','COO'] and arc_1[5] in speechV_ids):  # 还要处理COO 的情况
                                    speech_ = self.complete_VOB_server(arcs, child_dict_list, arc_1[2])
                                    if speech_:
                                        if arc_1[5] == speechV_ids[0] :#and arc_1[4] in self.speechV:
                                            # 主要动词是观点动词
                                            if len(speech_) < 10:
                                                if len(speechV_ids) > 1:
                                                    speechV = speechV + speech_
                                                else:
                                                    speech = speech_
                                            else:
                                                speech = speech_
                                        else:
                                            if arc_1[4] in self.speechV:
                                                speechV=speechV+arc_1[4]
                                                speech= speech +speech_ if speech !=None else speech_

                            if subject and speech:
                                    stuple[subject].append((speechV, speech))

        return ttuple, otuple, stuple

    def ruler_baidu(self, arcs):
        ttuple = defaultdict(list)
        try:
            for arc in arcs:
                if arc.get('postag') == 'nr':
                    # 但此人名不能作为其他元素的ATT
                    if arc.get('deprel') == 'ATT':
                        continue
                    person = arc.get('word')  # 这里再去对齐
                    print(person)
                    title, place, ttuple = self.find_title_baidu(arcs, arc.get("id"), '', '', ttuple, person)
                    if (title or place):
                        ttuple[person].append((title, place))
                    # 但此人名不能作为其他元素的ATT
                    # if arc[5] in [a[2] for a in arcs if a.get('deprel')=='ATT' and a[2]==arc[5]]:
                    #     continue
        except:
            None
        return ttuple

    def find_title_server(self, arcs, word_index):
        ttuple = defaultdict(list)
        person_or_place = arcs[word_index][1]
        title, place, ttuple = self.find_title(arcs, word_index, '', '', ttuple, person_or_place)
        if (title or place):  # 还要处理代词问题
            if title==place:
                title=''
            ttuple[person_or_place].append((title, place))
        # else:
        return title, place, ttuple

    def find_title1(self, arcs, word_index,  ttuple, person):
        titles=''
        #可否以符号来区分呢
        for arc in arcs:
            #这个地方应该进行改造，进行实体对齐，
            if(arc[0]=='ATT' and arc[5]==word_index and arc[4]==person):
                titles+=self.complete_VOB_server(arcs,'',arc[2])
                # titles=title.split('、')

        place = self.find_place(arcs, word_index)
        for t in titles.split('、'):
            if len(t) > 1:
                if place and t == place['name']:
                    t = ''
                ttuple[person].append((t, place))
        return ttuple

    def find_title(self, arcs, word_index, title, place, ttuple, person):
        for arc in arcs:
            # n-nh
            # ns-n-nh
            # n-n-nh
            # nd-n-nh
            #这个地方应该进行改造，进行实体对齐，
            if (arc[2] == word_index and arc[0] == 'ATT'):
                # if (arc[3] != 'ns' ):  # in ['n','ni','nd']):#nd-->前
                title += arc[1]
                if (arc[3]) == 'ns' or self.place_dict.get(arc[1]):
                    # ns要进行归一化对齐，看要哪一级的，如果是多级，变成一个链
                    place += arc[1]
            if (arc[5] == word_index and arc[0] == 'ATT'):
                title_, place_, ttuple = self.find_title(arcs, arc[2], '', '', ttuple, person)
                title = title + title_
                place = place + place_
                # ttuple.append((title,place))
                # title=''
                # place=''
            if (arc[5] == word_index and arc[0] == 'COO'):
                # 这是平行的一组

                title_, place_, ttuple = self.find_title(arcs, arc[2], '', '', ttuple, person)
                # if (arc[3] != 'ns'):
                title_ += arc[1]
                # if (arc[3]) == 'ns' or self.place_dict.get(arc[3]):
                #     place_ += arc[1]
                # print(title_,place_)
                place_=self.find_place(arcs,arc[2])
                ttuple[person].append((title_, place_))

        return title, place, ttuple

    def ruler3(self, arcs):

        ttuple = defaultdict(list)
        for arc in arcs:
            if arc[6] == 'nh':
                # 但此人名不能作为其他元素的ATT
                if arc[5] in [a[2] for a in arcs if a[0] == 'ATT' and a[2] == arc[5]]:
                    continue
                # ttuple = set()

                # person = ''
                person = arc[4]  # 这里再去对齐
                print(person)
                # <class 'list'>: ['ATT', '总书记', 1, 'n', '习近平', 7, 'nh']

                if (arc[0] == 'ATT' and arc[3] == 'n'):
                    # 这是第一个定语词
                    word_index = arc[2]
                    title, place, ttuple = self.find_title(arcs, word_index, '', '', ttuple, person)
                    if (title or place):
                        ttuple[person].append((title, place))

        # 要再去做地名对齐？
        return ttuple

    def ruler1(self, words, postags, roles_dict, role_index, child_dict_list):
        v = words[role_index]

        role_info = roles_dict[role_index]
        child_dict = child_dict_list[role_index]
        svos = []
        if 'A0' in role_info.keys() and 'A1' in role_info.keys():
            ps = []
            # o = ''.join([words[word_index] for word_index in range(role_info['A1'][1], role_info['A1'][2] + 1) if
            #              words[word_index]])
            # if('TMP' in role_info and role_info['TMP'][1]>role_index and role_info['TMP'][2]<role_info['A1'][1]):
            #     o=''.join([words[word_index] for word_index in range(role_info['TMP'][1], role_info['TMP'][2] + 1) if
            #              words[word_index]])+o
            # 这里要简化
            o = ''.join([words[word_index] for word_index in range(role_index + 1, role_info['A1'][2] + 1)])

            if (role_info['A0'][1] == role_info['A0'][2] and postags[role_info['A0'][1]] in ['nh', 'r']):
                # 只有一个主词A0
                tmp = ''
                # if(postags[role_info['A0'][1]]=='r'  ):
                # 如果是代词
                tmp = self.trans_pronoun(words[role_info['A0'][1]], postags, role_info['A0'][1])

                if tmp == None: return 4, []

                # else:
                #     tmp=words[role_info['A0'][1]]
                ps.append(tmp)
                svos.append([tmp, v, o])
            elif role_info['A0'][1] != role_info['A0'][2]:
                for index in range(role_info['A0'][1], role_info['A0'][2] + 1):
                    if (postags[index] in ['nh', 'r']):
                        tmp = self.trans_pronoun(words[index], postags, index)
                        if tmp == None: continue
                        # tmp=words[index]
                        ps.append(tmp)
                        svos.append([tmp, v, o])
                # None
            else:
                if ('SBV' in child_dict):
                    for index in child_dict['SBV']:
                        peoples = self.get_peoples(words, postags, child_dict_list, index)
                        for p in peoples:
                            tmp = self.trans_pronoun(words[p], postags, p)
                            if tmp == None: continue
                            ps.append(words[p])
                            # people = self.get_people(words, postags, child_dict_list, child_dict['SBV'][0])
                            # if people:
                            #     print(str(people) + words[people])
                            #     tmp=words[people]
                            svos.append([words[p], v, o])
            # 处理状语
            if 'TMP' in role_info and len(ps) > 0:
                for index in range(role_info['TMP'][1], role_info['TMP'][2] + 1):
                    if (index in roles_dict and postags[index] == 'v' and 'A1' in roles_dict[index]):
                        v = words[index]
                        role_info = roles_dict[index]
                        o = ''.join(
                            [words[word_index] for word_index in range(role_info['A1'][1], role_info['A1'][2] + 1) if
                             words[word_index]])
                        for p in ps:
                            svos.append([p, v, o])
                # for word_index in range(role_info['A0'][1], role_info['A0'][2] + 1):
                #
                #     if   postags[word_index] in ['nh'] and words[word_index]:
                #         tmp+=words[word_index]
                #     if  postags[word_index] not in ['nh']:#可能出现定语后置   习近平总书记
                #         child_dict=child_dict_list[word_index]
                #         e1,contain_people= self.complete_e(words,postags,child_dict_list,word_index)
                #         tmp=None
                #         break
            # s=tmp
            # s = ''.join([words[word_index] for word_index in range(role_info['A0'][1], role_info['A0'][2]+1) if
            #              postags[word_index] in ['nh'] and words[word_index]])
            # postags[word_index][0] not in ['w', 'u', 'x'] and words[word_index]])

            # postags[word_index][0] not in ['w', 'u', 'x'] and words[word_index]])
            # if s  and o:
            #     return '1', [s, v, o]
        if 'COO' in child_dict:
            # 说明还有并行的动词
            for coo in child_dict['COO']:
                if postags[coo] == 'v' and 'SBV' in child_dict and 'VOB' in child_dict_list[
                    coo] and coo not in roles_dict:
                    v = words[coo]
                    for index in child_dict['SBV']:
                        peoples = self.get_peoples(words, postags, child_dict_list, index)
                    e2 = self.complete_VOB(words, postags, child_dict_list, coo)
                    for p in peoples:
                        svos.append([words[p], v, e2])

        if len(svos) > 0:
            return '1', svos
        # elif 'A0' in role_info:
        #     s = ''.join([words[word_index] for word_index in range(role_info['A0'][1], role_info['A0'][2] + 1) if
        #                  postags[word_index][0] not in ['w', 'u', 'x']])
        #     if s:
        #         return '2', [s, v]
        # elif 'A1' in role_info:
        #     o = ''.join([words[word_index] for word_index in range(role_info['A1'][1], role_info['A1'][2]+1) if
        #                  postags[word_index][0] not in ['w', 'u', 'x']])
        #     return '3', [v, o]
        return '4', []

    '''三元组抽取主函数'''

    def ruler2(self, words, postags, child_dict_list, arcs, roles_dict):
        svos = []
        svos_hed = []
        # 一种特殊情况
        # 习近平强调，要营造有利于创新创业创造的良好发展环境。
        # 要向改革开放要动力，最大限度释放全社会创新创业创造动能，不断增强我国在世界大变局中的影响力、竞争力。
        # 第二句无主语
        hed_index = -1
        for arc in arcs:
            if (arc[0] == 'HED' and arc[3] == 'v'):
                print('HED is ' + arc[1])
                index = arc[2]
                hed_index = index
                child_dict = child_dict_list[index]
                if 'SBV' not in child_dict:
                    print('no subject but v is ' + arc[1])
                    return []

        for index in range(len(postags)):

            tmp = 1
            # 先借助语义角色标注的结果，进行三元组抽取
            if index in roles_dict:  # and arcs[index][0] == 'HED':
                # if :

                flag, triple = self.ruler1(words, postags, roles_dict, index, child_dict_list)
                if flag == '1':

                    if index == hed_index:
                        print('hed role_label_find:' + str(triple))
                        svos_hed += (triple)
                    else:
                        print('role_label_find:' + str(triple))
                        svos += (triple)
                    tmp = 0
                    # 如果说这里完全处理完了，后面就不用处理了。但COO 的情况没有处理。
            if tmp == 1 or True:
                # 如果语义角色标记为空，则使用依存句法进行抽取
                # if postags[index] == 'v':
                if postags[index]:
                    # if arcs[index][0]=='HED':
                    # 抽取以谓词为中心的事实三元组
                    child_dict = child_dict_list[index]
                    if 'SBV' in child_dict and 'COO' in child_dict:
                        # 会上，雷金玉、张林顺、兰平勇、康涛、陈国鹰、潘越、丁世忠、章联生等8位代表先后围绕打好脱贫攻坚战、建设美丽乡村、
                        # 发展远洋渔业、深化两岸融合发展、建设“数字中国”、扩大对外开放、推动创新发展、促进老区苏区发展等问题发表意见。
                        for coo in child_dict['COO']:
                            child_dict_coo = child_dict_list[coo]
                            if 'SBV' in child_dict_coo and 'VOB' in child_dict_coo:
                                r = words[coo]
                                for i in child_dict['SBV']:
                                    ps = self.get_peoples(words, postags, child_dict_list, i)
                                    for p in ps:

                                        e1 = self.trans_pronoun(words[p], postags, p)
                                        if e1 == None: continue
                                        # e1=words[p]
                                        e2 = ''.join(words[coo + 1:])
                                        svos.append([e1, r, e2])
                                        print('SBV+COO+VOB find:' + str([e1, r, e2]))

                    # 主谓宾
                    if 'SBV' in child_dict and 'VOB' in child_dict:
                        r = words[index]
                        # e1 = words[child_dict['SBV'][0]]# self.complete_e(words, postags, child_dict_list, child_dict['SBV'][0])
                        # e2 = ''.join(words[child_dict['VOB'][0]:])  #self.complete_e(words, postags, child_dict_list, child_dict['VOB'][0])
                        # 有可能出现SBV有多个的情况
                        for i in child_dict['SBV']:
                            # COO的怎么办
                            ps = self.get_peoples(words, postags, child_dict_list, i)
                            # e1, contain_people1 =self.complete_e(words, postags, child_dict_list, i)
                            # print(str(len(ps))+'  '+str(contain_people1))
                            # e2 = ''.join(words[child_dict['VOB'][0]:])
                            e2 = ''.join(words[index + 1:])
                            # e2, contain_people2 =self.complete_e(words, postags, child_dict_list, child_dict['VOB'][0])
                            for p in ps:
                                tmp = words[p]
                                # if postags[p] == 'r':
                                tmp = self.trans_pronoun(tmp, postags, p)
                                if tmp == None: continue
                                svos.append([tmp, r, e2])
                                print('SBV+VOB find:' + str([tmp, r, e2]))
                                # if 'COO' in child_dict:
                                #     for coo in child_dict['COO']:
                                #         if 'SBV' in child_dict_list[coo]:
                                #
                                #             # 这里其实也可能是有多个COO 的,这个是v的COO
                                #             ps = self.get_peoples(words, postags, child_dict_list, child_dict_list[coo]['SBV'][0])
                                #             print('COO:' + str([words[coo] for coo in child_dict['COO']]) + '  ' + words[index] + ' ps:' + str(ps))
                                # if 'VOB' in child_dict_list[coo]:可能在前面join全都处理了

                    # 定语后置，动宾关系
                    relation = arcs[index][0]
                    head = arcs[index][2]
                    if relation == 'ATT':
                        if 'VOB' in child_dict:
                            # e1,contain_people1 = self.complete_e(words, postags, child_dict_list, head - 1)
                            ps = self.get_peoples(words, postags, child_dict_list, head - 1)
                            if not ps: continue
                            e1 = words[ps[0]]
                            r = words[index]
                            # e2,contain_people2 = self.complete_e(words, postags, child_dict_list, child_dict['VOB'][0])
                            e2 = self.complete_VOB(words, postags, child_dict_list, child_dict['VOB'][0])
                            temp_string = r + e2
                            # if not (contain_people1):continue
                            if temp_string == e1[:len(temp_string)]:
                                e1 = e1[len(temp_string):]
                            if temp_string not in e1:
                                svos.append([e1, r, e2])
                                print('ATT+VOB find:' + str([e1, r, e2]))
                    # 含有介宾关系的主谓动补关系
                    if 'SBV' in child_dict and 'CMP' in child_dict:
                        e1, contain_people1 = self.complete_e(words, postags, child_dict_list, child_dict['SBV'][0])
                        cmp_index = child_dict['CMP'][0]
                        if not contain_people1: continue
                        r = words[index] + words[cmp_index]
                        if 'POB' in child_dict_list[cmp_index]:
                            e2, contain_people2 = self.complete_e(words, postags, child_dict_list,
                                                                  child_dict_list[cmp_index]['POB'][0])
                            svos.append([e1, r, e2])
                            print('SVB+CMP find:' + str([e1, r, e2]))
                    # if 'VOB' in child_dict and postags[index]=='v':
                    #     print(self.complete_VOB(words, postags, child_dict_list, index))
            if svos:
                self.last_people = svos[-1][0]
        if svos_hed: svos += svos_hed
        return svos

    def complete_ATT_server(self,arcs,child_dict_list,word_index):
        # word = arcs[word_index][1]
        prefix = ''
        # postfix = ''
        for arc in arcs:
            if arc[5] == word_index and arc[2] < word_index:
                prefix += self.complete_VOB_server(arcs, child_dict_list, arc[2])
            # if arc[5] == word_index and arc[2] > word_index:
            #     postfix += self.complete_VOB_server(arcs, child_dict_list, arc[2])
        return prefix

    # 服务器版的,完整化宾语，但下一句的后置宾语不能识别
    def complete_VOB_server(self, arcs, child_dict_list, word_index):

        word = arcs[word_index][1]
        prefix = ''
        postfix = ''
        for arc in arcs:
            if arc[5] == word_index and arc[2] < word_index:
                prefix += self.complete_VOB_server(arcs, child_dict_list, arc[2])
            if arc[5] == word_index and arc[2] > word_index:
                postfix += self.complete_VOB_server(arcs, child_dict_list, arc[2])
        return prefix + word + postfix


    def complete_VOB(self, words, postags, child_dict_list, word_index):
        cword = words[word_index]
        child_dict = child_dict_list[word_index]
        prefix = ''
        if 'ATT' in child_dict:
            for i in range(len(child_dict['ATT'])):
                prefix += self.complete_VOB(words, postags, child_dict_list, child_dict['ATT'][i])
        postfix = ''
        if postags[word_index] == 'v':
            # if 'SBV' in child_dict:
            #     prefix_, contain_people_ =self.complete_e(words, postags, child_dict_list, child_dict['SBV'][0])
            #     prefix+= prefix_
            if 'VOB' in child_dict:
                postfix += ''.join(
                    [words[word_index_] for word_index_ in range(word_index + 1, child_dict['VOB'][0] + 1) if
                     words[word_index_]])
                # postfix+=self.complete_VOB(words, postags, child_dict_list, child_dict['VOB'][0])
                return postfix

                print('SBV prefix:' + prefix)
        return prefix + words[word_index] + postfix

    def merge_svos(self, svos):
        tmp = []
        for svo in svos:
            flag = True
            for svo_ in svos:
                if svo_[2].find(svo[2]) > -1 and svo_[2] != svo[2]:
                    flag = False
            if (flag):
                tmp.append(svo)
        return tmp

    '''对找出的主语或者宾语进行扩展'''

    def complete_e(self, words, postags, child_dict_list, word_index):
        # 这里是嵌套的，要如何确定包含人名呢
        cword = words[word_index]
        contain_people = False
        child_dict = child_dict_list[word_index]
        prefix = ''
        if postags[word_index] == 'nh': contain_people = True
        if 'ATT' in child_dict:
            for i in range(len(child_dict['ATT'])):
                if (postags[child_dict['ATT'][i]] == 'nh'): contain_people = True
                prefix_, contain_people_ = self.complete_e(words, postags, child_dict_list, child_dict['ATT'][i])
                prefix += prefix_
                if (contain_people_):
                    contain_people = True
                    print('att prefix:' + prefix)
        postfix = ''
        if postags[word_index] == 'v':
            if 'VOB' in child_dict:
                if (str(child_dict['VOB'][0]).isnumeric() and postags[
                    child_dict['VOB'][0]] == 'nh'): contain_people = True
                postfix_, contain_people_ = self.complete_e(words, postags, child_dict_list, child_dict['VOB'][0])
                postfix += postfix_
                if (contain_people_):
                    contain_people = True
                print('VOB postfix:' + postfix)
            if 'SBV' in child_dict:
                prefix_, contain_people_ = self.complete_e(words, postags, child_dict_list, child_dict['SBV'][0])
                prefix += prefix_
                if (contain_people_):
                    contain_people = True
                print('SBV prefix:' + prefix)
            # if 'COO' in child_dict:
            #     for coo in child_dict['COO']:
            #         if 'VOB' in child_dict_list[coo]:
            #             postfix_, contain_people_ = self.complete_e(words, postags, child_dict_list,
            #                                                         child_dict_list[coo]['VOB'][0])
            #             postfix+=postfix_
            #             print('COO VOB postfix_:' + postfix_)

        return prefix + words[word_index] + postfix, contain_people

    def w2file(self, svos):

        for svo in svos:
            self.out.write(svo[0] + '\t' + svo[1] + '\t' + svo[2] + '\n')

        print(set([svo[1] for svo in svos]))

    def main(self):
        # 1
        rows = self.query_country_name('%习近平%')
        self.lookforpeoples = ['习近平']
        svos = []
        self.ners = ['nh']
        for row in rows:
            content = row[1]
            # content='会上，雷金玉、张林顺、兰平勇、康涛、陈国鹰、潘越、丁世忠、章联生等8位代表先后围绕打好脱贫攻坚战、建设美丽乡村、发展远洋渔业、深化两岸融合发展、建设“数字中国”、扩大对外开放、推动创新发展、促进老区苏区发展等问题发表意见。'
            # content='中共中央总书记、国家主席、中央军委主席习近平，中共中央政治局常委、全国人大常委会委员长栗战书，中共中央政治局常委、全国政协主席汪洋，中共中央政治局常委、中央书记处书记王沪宁，中共中央政治局常委、中央纪委书记赵乐际，10日分别参加了十三届全国人大二次会议一些代表团的审议。'
            # content='要向改革开放要动力，最大限度释放全社会创新创业创造动能，不断增强我国在世界大变局中的影响力、竞争力。'
            # content='在认真听取娄勤俭、吴政隆、车捷等代表发言后，栗战书说，制定外商投资法是以习近平同志为核心的党中央确定的重大立法任务，充分彰显了党和人民在新时代将改革开放进行到底的坚定决心，宣示了我国奉行互利共赢开放战略、积极推动建设开放型世界经济的鲜明立场，有利于打造市场化、法治化、国际化的一流营商环境，为推动高水平对外开放提供更加有力的法治保障。'
            # content='中共中央总书记、国家主席、中央军委主席习近平12日下午在出席十三届全国人大二次会议解放军和武警部队代表团全体会议时强调，今年是全面建成小康社会、实现第一个百年奋斗目标的关键之年，也是落实我军建设发展“十三五”规划、实现国防和军队建设2020年目标任务的攻坚之年，全军要站在实现中国梦强军梦的高度，认清落实“十三五”规划的重要性和紧迫性，坚定决心意志，强化使命担当，锐意开拓进取，全力以赴打好规划落实攻坚战，确保如期完成既定目标任务。'
            # content='3月12日下午，中共中央总书记、国家主席、中央军委主席习近平出席十三届全国人大二次会议解放军和武警部队代表团全体会议并发表重要讲话。'
            # content='12日下午，中共中央总书记、国家主席、中央军委主席习近平来到京西宾馆，出席十三届全国人大二次会议解放军和武警部队代表团全体会议并发表重要讲话，强调要站在实现中国梦强军梦的高度，认清落实我军建设发展“十三五”规划的重要性和紧迫性，坚定决心意志，强化使命担当，锐意开拓进取，全力以赴打好规划落实攻坚战，确保如期完成既定目标任务。'
            # content='楚雄彝族自治州委组织部干部李育斌表示，《通知》为基层减负作出明确部署，让广大党员干部有更多的时间深入一线、深入群众，集中精力全心全意为群众办实事、办好事。'
            # content='报道称，哈利勒扎德目前正在返回华盛顿，但他表示，他将“很快”再次与塔利班进行会晤。'
            # content='同时，威廉姆斯也表示，应该对潜在的不稳定因素提高警惕。他说，美联储将根据最新的数据，更为灵活地制定加息计划。 '
            # content='国会众议院议长、民主党人佩洛西11日发表声明，抨击白宫为修建边境墙提出的拨款要求'
            # content='白宫国家经济委员会主任拉里·库德洛接受采访时披露，特朗普寻求为修建“边境墙”拨款86亿美元，远高于去年所提57亿美元建墙拨款。'
            # content='“他不愿意对谈判结果作出预测，也不愿透露何时会完成谈判，但他暗示谈判结果“不久”将揭晓。”'
            # content='他不愿意对谈判结果作出预测'
            print(content)

            content = self.remove_noisy(content)
            if content.find('日电') > -1:
                content = content[content.find('日电') + 2:]
            self.init()

            # 对文章进行长句切分处理
            sents = self.seg_content(content)

            # ner_sents保存具有命名实体的句子
            ner_sents = []
            # ners保存命名实体
            ners = []
            # triples保存主谓宾短语
            triples = []
            # 存储文章事件
            events = []

            for sent in sents:  # subsents:
                print(sent)
                # str(sent).strip()
                words, postags, child_dict_list, roles_dict, arcs = self.parser_main(sent)
                # if('nh' not in postags):
                #     print('no people in sentence')
                #     print('*'*15)
                #     continue
                # print(postags)
                # words, postags = self.basic_process(sent.strip())
                # words_list += [[i[0], i[1]] for i in zip(words, postags)]
                # subsents_seg.append([i[0] for i in zip(words, postags)])

                svo = self.ruler2(words, postags, child_dict_list, arcs, roles_dict)
                # ner = self.collect_ners(words, postags)
                if (len(svo) > 0):
                    print(child_dict_list)
                    print(roles_dict)
                    print(arcs)
                    print(svo)
                print(list(zip(words, postags)))

                print('*' * 15)
                svos += svo
                if svo: self.last_sent_people = svo[0][0]
            self.release()
            svos = self.merge_svos(svos)
            self.w2file(svos)
        self.out.close()
        #     if ner:
        #         triple = self.extract_triples(words, postags)
        #         if not triple:
        #             continue
        #         triples += triple
        #         ners += ner
        #         ner_sents.append([words, postags])
        # print(ner_sents)
        # print(triples)

    def neo_person_title(self):
        self.global_ttuple = defaultdict(list)
        rows = self.query_country_name('%')
        self.ners = ['nh']
        self.init()
        for i, row in enumerate(rows):
            content = row[1]
            # content='中共中央总书记、中华人民共和国主席、中央军委主席、中央军委主席习近平，中共中央政治局常委、全国人大常委会委员长栗战书，中共中央政治局常委、全国政协主席汪洋，中共中央政治局常委、中央书记处书记王沪宁，中共中央政治局常委、中央纪委书记赵乐际，10日分别参加了十三届全国人大二次会议一些代表团的审议。'
            # content='剑桥全球咨询主席道格拉斯·卢特说：“当下各国应该多思考合作，而非竞争。这是中国的主张，也是多数人的想法。”'
            # content='一方面，日本在AIP技术上积累不足，之前必须仰赖进口的小功率斯特林发动机满足本国需求；'
            # content='通海县九龙街道大梨社区党总支书记李光焰表示：“文山会海、督查考核过度留痕，占用了我们大量的时间和精力，如果能够解决这些问题，改善时常‘疲于应付’的窘境，我们至少可以腾出三分之一的时间来，为社区居民多做些实实在在的事。'
            content = '谈及美国以所谓“安全威胁”为由打压中国高科技企业，马尔科表示，美国必须提供有说服力的证据，否则指控只是猜测而已。马尔科希望，中美两国能以建设性的方式解决贸易分歧，“贸易战没有赢家，应尽快找到和平解决方案”。\
                　　摩尔多瓦共产党人党意识形态秘书康斯坦丁·斯塔里什说，近几十年，全球经济体系已被证实行之有效，并推动了各国经济和贸易发展。如今，美国借保护自身经济利益为由，破坏这一体系基础，这好比“大象闯进瓷器店”，破坏了现有模式，却又不提供替代方案。\
                　　斯塔里什认为，美国盲目挑起经贸摩擦，是为保持自身“世界经济霸主地位”，此举严重违背市场规律，表明美国不愿对世界经济发展负责，同时也将影响美国自身经济发展。\
                　　巴勒斯坦法塔赫革命委员会委员巴萨姆说，美国挑起对华贸易摩擦的行为是“霸凌逻辑”，贸易战对中美双方都会造成损失。\
                　　巴勒斯坦人民党总书记萨利希指出，美国此举违背市场规律和国际贸易规则，不仅对美国和中国，乃至对世界经济都造成威胁。此外，美国对华为等中国企业进行打压，是因为相关企业具有强劲的全球竞争力。（执笔记者：马湛；参与记者：张修智、林惠芬、陈进、杨媛媛、赵悦、周天翮）'
            content = self.remove_noisy(content)
            if content.find('日电') > -1:
                content = content[content.find('日电') + 2:]
            # self.init()
            sents = self.seg_content(content)
            # 这里其实应该抽关键句
            for sent in sents:

                arcs, child_dict_list = self.parser_main_ltpserver(sent)
                # arcs=self.parser_main_baidu(sent)
                # ttuple=self.ruler_baidu(arcs)
                #
                ttuple = self.ruler3(arcs)
                # self.global_ttuple.update(ttuple)
                if len(ttuple) > 0:
                    print(sent)
                    print(ttuple)
                    print(i, '*' * 15)
            # self.release()
        print(self.global_ttuple)
        # fou = open('./mod/global_ttuple.bin', 'wb')
        # pickle.dump(self.global_ttuple, fou)
        # fou.close()

    def checkPersonKG(self):
        personKG = PersonKG()
        load_file = open('./mod/global_ttuple.bin', 'rb')
        self.person_dict = pickle.load(load_file)
        fou = open('./resources/person_tuple', 'w', encoding='utf-8')
        for person in self.person_dict:
            if personKG.person_dict.get(person):
                kgps = personKG.person_dict.get(person)
                if len(kgps) == 1:
                    kgp = personKG.person_index.get(kgps[0].get("id"))
                    # 就是这个人
                    # personIndex[person.identity] = {'name': person.get('name'), 'nationality': person.get('国籍'),
                    #                                 'catalog': person.get('类别'), 'job': person.get('职务'),
                    #                                 'job1': person.get('职务简称'), 'ename': person.get('英文名')}
                    for ttuple in self.person_dict.get(person):
                        # 机构名未统一，中央军委委员---》中共中央军委委员
                        # 机器如何确认一部分，当数量超过2，才头发
                        fou.write(
                            kgp.get("name") + "\t" + kgp.get("nationality") + "\t" + kgp.get('job') + '\t' + kgp.get(
                                'job1') + '\t' + ttuple[0] + "\t" + ttuple[1] + '\n')
                # 可能有重名
                # for kgp in kgps:

        fou.close()

    def speechCollect(self):
        self.neoManager.clear()
        self.tn = TimeNormalizer()

        load_file = open('./mod/place_dict.bin', 'rb')
        self.place_dict = pickle.load(load_file)
        load_file = open('./mod/place_index.bin', 'rb')
        self.place_index = pickle.load(load_file)

        # 还要去掉一些错词
        with open('./resources/place_remove.txt', 'r', encoding='utf-8') as f:
            for line in f.readlines():
                line = line.strip()
                self.place_dict.pop(line)
        #把中方、美方加上
        for p in self.place_index:
            if self.place_index[p]['level']=='2':#国家
                self.place_dict[self.place_index[p]['name'][0]+'方'].append({'id':p,'pid':self.place_index[p]['pid']})

        logging.info('place count %d,place name count:%s' % (len(self.place_index), len(self.place_dict)))


        rows = self.query_country_name('%美国%')
        # svos = []
        for i, row in enumerate(rows):
            uuid=row[0]
            content = '国会众议院议长、民主党人佩洛西11日发表声明，抨击白宫为修建边境墙提出的拨款要求。'
            # content = '谈及美国以所谓“安全威胁”为由打压中国高科技企业，马尔科表示，美国必须提供有说服力的证据，否则指控只是猜测而已。马尔科希望，中美两国能以建设性的方式解决贸易分歧，“贸易战没有赢家，应尽快找到和平解决方案”。\
            #     　　摩尔多瓦共产党人党意识形态秘书康斯坦丁·斯塔里什说，近几十年，全球经济体系已被证实行之有效，并推动了各国经济和贸易发展。如今，美国借保护自身经济利益为由，破坏这一体系基础，这好比“大象闯进瓷器店”，破坏了现有模式，却又不提供替代方案。\
            #     　　斯塔里什认为，美国盲目挑起经贸摩擦，是为保持自身“世界经济霸主地位”，此举严重违背市场规律，表明美国不愿对世界经济发展负责，同时也将影响美国自身经济发展。\
            #     　　巴勒斯坦法塔赫革命委员会委员巴萨姆说，美国挑起对华贸易摩擦的行为是“霸凌逻辑”，贸易战对中美双方都会造成损失。\
            #     　　巴勒斯坦人民党总书记萨利希指出，美国此举违背市场规律和国际贸易规则，不仅对美国和中国，乃至对世界经济都造成威胁。此外，美国对华为等中国企业进行打压，是因为相关企业具有强劲的全球竞争力。（执笔记者：马湛；参与记者：张修智、林惠芬、陈进、杨媛媛、赵悦、周天翮）'
            # content = '波兰担忧俄罗斯军事活动，数月前开始游说美国在波兰设立永久性军事基地。美方官员暗示，这一提议恐怕不会获得采纳。不少分析师认为，在波兰长期驻军成本高，不符合特朗普在全球多地减少美国军事存在的主张。'
            # content = '中共中央总书记、中华人民共和国主席、中央军委主席、中央军委主席习近平，中共中央政治局常委、全国人大常委会委员长栗战书，中共中央政治局常委、全国政协主席汪洋，中共中央政治局常委、中央书记处书记王沪宁，中共中央政治局常委、中央纪委书记赵乐际，10日分别参加了十三届全国人大二次会议一些代表团的审议。'
            # content='此外,新加坡民航管理局也在12日宣布暂停737MAX所有型号客机在新加坡机场起降。'
            # content='我们要学会表达和暗示。'
            # content='论文作者之一、泛生子基因公司首席执行官王思振介绍，这项技术方法在本次研究中能够发现小于3厘米的早期肝癌。'
            # content='身为一名活跃在国际时尚舞台的著名高定服装设计师，郭培说自己其实是和改革开放后的中国时尚一起成长的。'
            content = row[1]
            news=self.neoManager.get_node(str(uuid),'news')
            #这里还应该得到新闻的时间
            self.neoManager.update_node(news,{'uuid':uuid,'content':content})

            content = self.remove_noisy(content)
            if content.find('日电') > -1:
                content = content[content.find('日电') + 2:]
            sents = self.seg_content(content)

            self.places = set()
            self.last_people=''
            for sent in sents:
                arcs, child_dict_list = self.parser_main_ltpserver(sent)
                print(sent)
                print(arcs)
                ttuple, otuple, stuple = self.ruler_speech(arcs, child_dict_list,sent)
                # 再单独处理每个三元组

                self.merge_ttuple(ttuple,otuple,stuple,sent,news)

                for triplet in ttuple:
                    if self.neoManager.check_node(triplet, 'person'):
                        self.last_people=triplet
                for triplet in stuple:
                    if self.neoManager.check_node(triplet, 'person'):
                        self.last_people=triplet
                # svos += svo
                # if svo: self.last_sent_people = svo[0][0]
            # self.release()
            # svos = self.merge_svos(svos)

    def merge_ttuple(self, ttuple, otuple, stuple,sentance,news):
        for triplet in ttuple:
            # 先判断有没有？？
            # person=Node('Person', name='张三', key='s')
            # 这里的人物和地名，还应该应用实体对齐
            for person in ttuple[triplet]:
                title = person[0]
                place = person[1]
                # if place!='' or place!=None:
                person_node=self.neoManager.get_node(triplet, 'person')
                title_node =None
                place_node=None

                if title != '':
                    # data.append({'triplet': dict(zip(['entity1', 'relation', 'entity2', 'type1', 'type2'],
                    #                                  (triplet, 'title', title, 'person', 'title')))})
                    title_node=self.neoManager.get_node(title, 'title')
                    self.neoManager.add_relationship(person_node,title_node, 'title')

                if place != '' and place!=None:
                    place_node = self.neoManager.get_node(place['name'], 'place')
                    self.neoManager.update_node(place_node, place)
                    # person_node=self.neoManager.get_node(triplet, 'person')
                    self.neoManager.add_relationship(person_node, place_node, 'belong')

                    # data.append({'triplet': dict(zip(['entity1', 'relation', 'entity2', 'type1', 'type2'],
                    #                                  (triplet, 'belong', place, 'person', 'place')))})
                # if title != '' and (place != '' or place !=None):
                if title_node and place_node:
                    self.neoManager.add_relationship(title_node, place_node, 'belong')
                    # data.append({'triplet': dict(zip(['entity1', 'relation', 'entity2', 'type1', 'type2'],
                    #                                  (title, 'belong', place, 'title', 'place')))})
                # try:
                #     self.neoManager.write2db(data)
                # except:
                #     None
                # p=self.neoManager.get_node(triplet,'person')
                self.neoManager.add_relationship(news,person_node,'relate')


        for triplet in otuple:
            # 先判断有没有？？
            # person=Node('Person', name='张三', key='s')
            # 这里的人物和地名，还应该应用实体对齐
            for org in otuple[triplet]:
                title = org[0]
                place = org[1]
                org_node = self.neoManager.get_node(triplet, 'organization')
                title_node = None
                place_node = None
                if title != '':

                    title_node=self.neoManager.get_node(title, 'title')
                    self.neoManager.add_relationship(org_node,title_node, 'title')
                if place != '' and place!=None:
                    place_node = self.neoManager.get_node(place['name'], 'place')
                    self.neoManager.update_node(place_node, place)
                    self.neoManager.add_relationship(org_node, place_node, 'belong')
                if title_node and place_node:
                    self.neoManager.add_relationship(title_node, place_node, 'title')

        for triplet in stuple:
            # 先判断有没有？？
            # person=Node('Person', name='张三', key='s')
            # 这里要识别主语是什么，有一些技术型，北京方面认为，白宫XXX ，华盛顿XX ，美方XX  ，也要对刘成地点
            # tx = self.neoManager.graph.begin()
            for speech in stuple[triplet]:
                v = speech[0]
                content = speech[1]

                speech_node=self.neoManager.get_node(content,'speech')
                self.neoManager.update_node(speech_node,{'sentance':sentance,'uuid':news['uuid']})
                self.neoManager.add_relationship(news,speech_node,'include')
                # speech_node['sentance']=sentance
                # speech_node['uuid']=uuid
                # speech_node.update({'sentance':content})
                # tx.push(speech_node)
                # tx.commit()
                data = []
                #还应该放进原句，还是新闻的ID
                if self.neoManager.check_node(triplet, 'person'):
                    data.append({'triplet': dict(zip(['entity1', 'relation', 'entity2', 'type1', 'type2'],
                                                     (triplet, v, content, 'person', 'speech')))})
                elif self.neoManager.check_node(triplet, 'place'):
                    data.append({'triplet': dict(zip(['entity1', 'relation', 'entity2', 'type1', 'type2'],
                                                     (triplet, v, content, 'place', 'speech')))})
                elif self.neoManager.get_node(triplet, 'someone'):
                    #这里应该再进行一次实体对齐
                    data.append({'triplet': dict(zip(['entity1', 'relation', 'entity2', 'type1', 'type2'],
                                                     (triplet, v, content, 'someone', 'speech')))})
                # self.neoManager.graph.
                self.neoManager.write2db(data)


if __name__ == '__main__':
    handler = LtpParser()
    # handler.main()
    # handler.neo_person_title()
    handler.speechCollect()
# handler.checkPersonKG()