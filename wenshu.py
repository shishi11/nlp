'''
对法院执行案件进行抽取，
现在从北京审判信息抽取，后面可能从裁判文书网处理
现在只用了正则抽取，后面还想用深度学习进行细分类
未来从终本案件信息中筛选大额项目，进行申请执行人和被执行人的关联，找到原来是被告
但现在作为原告执行回一部分钱，这样就可以找到第一个案子的申请执行人，恢复执行。
临时附带收集，出现金额的情况、公司信息、个人信息

'''
import pprint
import re
import ahocorasick
import time

# import duckling as duckling
import execjs
from lxml.html.clean import unicode
import chinese2digits as c2d

from textProcess import TextProcess
import logging
import pickle
import collections
from pyhanlp import *
from urllib import request
from lxml import etree
from urllib import parse
import pandas
# from duckling import *

# import pyltp
logging.basicConfig(level=logging.INFO)
logging = logging.getLogger(__name__)

class Wenshu():

    def __init__(self):
        # print(text)
        # self.text=text
        # self.textProcess=TextProcess()
        self.aho_policical_person = ahocorasick.Automaton()
        self.regulars=[]
        #应该有三四种抽取方式
        #这是触发词+依存
        self.aho_policical_person.add_word('申请执行人', [
            {'word':'申请执行人','key': '申请执行人', 'field': 6, 'ekey': 'claimant',
             'rel': '申请执行人[）]?[：|:]?(.*?)[，|,][男|女|住]',
             'extrctor': 'regular'},
            # {'key': '申请执行人', 'field': 6, 'ekey': 'claimant', 'rel': '定中关系',
            #  'extrctor': 'pd'},
        ])
        self.aho_policical_person.add_word('被执行人', [{'word':'被执行人','key': '被执行人', 'field': 7, 'ekey': 'respondent',
                                                     'rel': '被执行人[）]?[：|:]?(.*?)[，|,][男|女|住]',
                                                     'extrctor': 'regular'},
                                                    # {'key': '被执行人', 'field': 7, 'ekey': 'respondent', 'rel': '定中关系',
                                                    #  'extrctor': 'pd'}
                                                    ])
        self.aho_policical_person.add_word('审判员',[{'word':'审判员','key': '审判员', 'field': 12, 'ekey': 'judger', 'rel': '审判员(.*)',
                                                     'extrctor': 'regular'}])
        self.aho_policical_person.add_word('审判长', [{'word':'审判长','key': '审判员', 'field': 12, 'ekey': 'judger', 'rel': '审判长(.*)',
                                                    'extrctor': 'regular'}])
        self.aho_policical_person.add_word('执行员', [
            {'word': '执行员', 'key': '审判员', 'field': 12, 'ekey': 'judger', 'rel': '审判长(.*)',
             'extrctor': 'regular'}])
        m=r'((?:[一二三四五六七八九十千万亿兆幺零百壹贰叁肆伍陆柒捌玖拾佰仟]+(?:点[一二三四五六七八九幺零]+){0,1})|\d+(?:[\.,，]\d+)*万?)元'
        # ' ((?:[一二三四五六七八九十千万亿兆幺零百]+(?:点[一二三四五六七八九幺零]+){0,1})|\d+(?:[\.,，]\d+)+万?)元'
        m1=r'(?:支付|给付|清偿|偿还|退赔).*?'+m
        #清偿 偿还  执行到位
        #标的还剩，XXX未执行到位 未执行到位
        #
        shean=[{'key': '标的', 'field': 8, 'ekey': 'judger','word':'标的',
          'rel': m1,
          'extrctor': 'regular'}]
        self.aho_policical_person.add_word('支付', shean)
        self.aho_policical_person.add_word('给付', shean)
        self.aho_policical_person.add_word('清偿', shean)
        self.aho_policical_person.add_word('偿还', shean)
        self.aho_policical_person.add_word('退赔', shean)

        self.aho_policical_person.add_word('执行标的', [{'key': '标的', 'field': 8, 'ekey': 'judger','word':'执行标的',
          'rel': '执行标的.*?'+m,
          'extrctor': 'regular'}])
        self.aho_policical_person.add_word('执行总标的', [{'key': '标的', 'field': 8, 'ekey': 'judger','word':'执行总标的',
                                                     'rel': '执行总标的.*?' + m,
                                                     'extrctor': 'regular'}])

        self.aho_policical_person.add_word('执行到位', [{'key': '执行到位', 'field': 9, 'ekey': 'judger', 'word': '执行到位',
                                                     'rel': '^(?:(?!未).)*执行到位.*?' + m,
                                                     'extrctor': 'regular'}])
        self.aho_policical_person.add_word('扣划', [{'key': '执行到位', 'field': 9, 'ekey': 'judger', 'word': '扣划',
                                                     'rel': '扣划.*?' + m,
                                                     'extrctor': 'regular'}])

        self.aho_policical_person.add_word('未执行到位', [{'key': '未执行到位', 'field': 9, 'ekey': 'judger', 'word': '未执行到位',
                                                     'rel': '未执行到位.*?' + m,
                                                     'extrctor': 'regular'}])

        self.aho_policical_person.add_word('终结', [{'key': '结果类型', 'field': 14, 'ekey': 'result_tag', 'word': '终结','value':'终结本案',
                                                      'rel': '(终结(.*)本次执行程序|本次执行程序终结)',
                                                      'extrctor': 'regular'}])
        self.aho_policical_person.add_word('中止', [
            {'key': '结果类型', 'field': 14, 'ekey': 'result_tag', 'word': '中止', 'value': '中止执行',
             'rel': '(中止(.*)执行程序|执行程序中止)',
             'extrctor': 'regular'}])
        self.aho_policical_person.add_word('审查', [
            {'key': '结果类型', 'field': 14, 'ekey': 'result_tag', 'word': '审查程序', 'value': '终结审查',
             'rel': '(终结(.*)审查程序|审查程序终结|审查终结)',
             'extrctor': 'regular'}])
        self.aho_policical_person.add_word('刑事判决', [
            {'key': '结果类型', 'field': 14, 'ekey': 'result_tag', 'word': '刑事判决', 'value': '刑事',
             'rel': '(刑事(判决|审判))',
             'extrctor': 'regular'}])

        self.aho_policical_person.add_word('撤销', [
            {'key': '结果类型', 'field': 14, 'ekey': 'result_tag', 'word': '撤销', 'value': '撤销',
             'rel': '(撤销.*?(冻结|查封))',
             'extrctor': 'regular'}])
        # 驳回
        self.aho_policical_person.add_word('驳回', [
            {'key': '结果类型', 'field': 14, 'ekey': 'result_tag', 'word': '驳回', 'value': '驳回',
             'rel': '(驳回.*?(请求|申请|异议))',
             'extrctor': 'regular'}])
        # self.aho_policical_person.add_word('')

        #数据结构：
        # 0审理法院、 必      ok
        # 1案件类型、 必      ok
        # 2案由、      必       ok
        # 3文书类型、  必     ok
        # 4案号、      必       ok
        # 5裁判日期、  必     ok
        # 6申请执行人、  必    ok
        # 7被执行人[]，  必       ok
        # 8标的金额，    选
        # 9执行金额，    选
        # 10是否执行完，  必
        # 11是否终结本次，    必    ok
        # 12审判员，      必
        # 13相关判决书，      必
        # 14细类型    选-----》追加或撤销追加，撤回执行，终结审查程序,驳回  移送  中止  变更申请人
        self.aho_policical_person.make_automaton()

        #预读取数据
        try:
            self.casepd = pandas.read_csv('./resources/case_detail_list.csv',index_col=0)
        except:
            self.casepd = pandas.DataFrame()
        # self.meta_person=pandas.DataFrame(columns=['name','detail'])

        try:
            self.meta_company=pandas.read_csv('./resources/company_list.csv',index_col=0)
            self.meta_company=self.meta_company.drop_duplicates(subset=None)
        except:
            self.meta_company = pandas.DataFrame(columns=['name', 'detail'])
        self.moneysent=[]
        # self.duckling = DucklingWrapper(language=Language.CHINESE)
        # casedict=self.casepd.to_dict()
        # print(casedict)



    def getSents(self,html,userPd=True):
        str=re.sub('</?\w+[^>]*>', '', html).strip()
        # str=self.textProcess.delSpace(str)
        sents=[re.sub('\s','',sentence) for sentence in re.split(r'[？?！!。;；\n\r]', str) if sentence]
        # sents = [sentence for sentence in self.cut_sent(str) if sentence]
        #已经分好句了
        # sents=[re.sub('\s','',sentence) for sentence in sents]

        parseDependency=[HanLP.parseDependency(sent) for sent in sents] if userPd else []

        return sents,parseDependency

    #句法分析，得到词之间的关系
    def parseSent(self,sent,pd,rule):
        # pd
        # print(sentence)
        str=None
        for word in pd.iterator():
            # print("%d %s/%s --(%s)--> %s（%s）" % (word.ID, word.LEMMA, word.POSTAG, word.DEPREL, word.HEAD.LEMMA, word.HEAD.ID))
            if word.LEMMA==rule['key'] and word.DEPREL==rule['rel'] and word.ID<word.HEAD.ID and len(word.HEAD.LEMMA)>1:#and sent.find(rule[1]['include']>-1):
                # pass
                # if sent.find('住所地')>-1 or sent.find('男')>-1 or sent.find('女')>-1:
                if word.HEAD.LEMMA.find('公司')>-1 or word.HEAD.POSTAG=='nr':
                    str=self.complete_VOB(word.HEAD,pd,word)
                    # if word.HEAD.LEMMA
                    if str.find('公司')<0:
                        if word.HEAD.POSTAG=='nr':
                            str=word.HEAD.LEMMA
                        else:
                            str=None


                # print('-'*24+str)
                # self.caseinfo[rule[1]['key']]=str
                # pprint.pprint(HanLP.segment(sent))
                # str=pd[word.ID:word.HEAD.ID]

        return str

    def complete_VOB(self, word,pd,exception):
        str=''
        for word_ in pd.iterator():
            if word_.HEAD==word and word_!=exception and word_.DEPREL=='定中关系' and word_.ID>exception.ID:
                str=str+self.complete_VOB(word_,pd,exception)
            if word_.ID>=word.ID:break
        #也可能没有定中关系
        str=str+word.LEMMA
        return str

    #获取案件信息
    def getCaseInfo(self,sents,pd,info):

        caseinfo = collections.defaultdict(list)
        for i,sent in enumerate(sents):
            #这是先用多模匹配，再用句法依存。
            for word in self.aho_policical_person.iter(sent):
                # pprint.pprint(word)
                # pprint.pprint(sent)
                #这里应该有两种规则类模式。一种是用定中关系，一种是用正则
                #其它方式，可以是直接用xpath取得结构化数据，
                #最难的是用深度学习来抽取
                for r in word[1]:

                    if r['field'] in [6,7] and r['extrctor']=='pd' :#and self.caseinfo.get(word[1]['key'])==None:
                        str=self.parseSent(sent,pd[i],r)

                        if str!=None:
                            if caseinfo[r['key']]!=None and str not in caseinfo[r['key']]:
                                caseinfo[r['key']].append(str)
                            if caseinfo[r['key']]==None:
                                caseinfo[r['key']].append(str)
                            break
                    if  r['extrctor'] == 'regular':
                        maohao=re.search(r['rel'],sent,re.I | re.DOTALL)
                        # print(sent,maohao)
                        if maohao!=None:
                            value=maohao.group(1)
                            #这里要把金额统一
                            if r['field'] in [8,9]:

                                money=re.sub('[,，]','',value)
                                #这里可能会报错，要小心
                                money_std=c2d.takeNumberFromString(money)['digitsStringList'][0]
                                value= money_std
                            if r['field'] in [14]:
                                value=r['value']
                            caseinfo[r['key']].append(value)
                            if r['field'] in [6, 7] :#元数据，暂不考虑重复因素
                                metadata=sent[sent.find(maohao.group(1))+len(maohao.group(1))+1:]
                                metadata=re.sub('，', ',', metadata)

                                if sent.find('住所地')>-1:
                                    # pmeta=pandas.DataFrame([{'name': maohao.group(1), 'detail': metadata}])
                                    self.meta_company=self.meta_company.append([{'name': maohao.group(1), 'detail': metadata}],ignore_index=True)
                                    # self.meta_company
                            break



            if sent.find('裁定如下：')>-1:
                reslut_flag=True
            # if reslut_flag and re.match(r'(?!未)终结(.*)本次执行程序|本次执行程序终结',sent)!=None:
            #     print(sent)
            # caseinfo['结果类型']='终结本案'
            #关联案件 京0102执恢223号  （2018）京0105民初92991号
            m=re.search('[\(（]\d{4}[\)）]\D{1}\d{2,4}\D{1,2}\d{2,5}号',sent)
            if m!=None :
                m=m.group()
                m=re.sub('（','(',m)
                m = re.sub('）', ')', m)
                if m!=info['case_code'] :
                    caseinfo['关联案号'].append(m)
            m = r'((?:[一二三四五六七八九十千万亿兆幺零百壹贰叁肆伍陆柒捌玖拾佰仟]+(?:点[一二三四五六七八九幺零]+){0,1})|\d+(?:[\.,，]\d+)*万?)元'
            if re.search(m,sent)!=None:
                self.moneysent.append(sent)
            # print(self.duckling.parse_money(sent))
        #各种情况可能造成，一些信息不全，需要采用别的手段进行补充，像是深度学习的部分
        return caseinfo



    def cut_sent(para,other=''):
        if(other==''):
            para = re.sub('([。！？\?])([^”])', r"\1\n\2", para)  # 单字符断句符
        else:
            para = re.sub('([ 。！？\?])([^”])', r"\1\n\2", para)  # 单字符断句符a
        para = re.sub('(\.{6})([^”])', r"\1\n\2", para)  # 英文省略号
        para = re.sub('(\…{2})([^”])', r"\1\n\2", para)  # 中文省略号
        # para = re.sub('(”)', '”\n', para)  # 把分句符\n放到双引号后，注意前面的几句都小心保留了双引号
        para = para.rstrip()  # 段尾如果有多余的\n就去掉它
        # 很多规则中会考虑分号;，但是这里我把它忽略不计，破折号、英文双引号等同样忽略，需要的再做些简单调整即可。
        return para.split("\n")
    #检查一下解析后的结果，有一些是必填，有一些是选填
    def check(self,caseinfo):
        pass

    def saveCase(self,case):
        pass
    #临时，应该用爬虫来做
    def getCaseHTML(self):
        URL='http://www.bjcourt.gov.cn/cpws/index.htm?st=1&q=&sxnflx=0&prompt=&dsrName=&ajmc=&ajlb=8&jbfyId=&zscq=&ay=&ah=&cwslbmc=&startCprq=&page='
        #取得目录
        case_list = []
        repeatFlag=False
        for i in range(20)[1:]:
            url=URL+str(i)
            html=request.urlopen(url).read().decode('utf-8').replace('&nbsp;', '')
            selector = etree.HTML(html)

            case_title_lis=selector.xpath('//ul[@class="ul_news_long"]/li')
            for case_title_li in case_title_lis:

                case_title={}
                case_title['title']=case_title_li.xpath('./a')[0].text.strip()
                case_title['url'] = case_title_li.xpath('./a')[0].attrib['href']
                case_title['court']= case_title_li.xpath('./span/span[@class="sp_name"]')[0].text.strip()
                case_title['sp_time']=case_title_li.xpath('./span/span[@class="sp_time"]')[0].text.strip()
                if len(self.casepd)>0 and case_title['url'] in self.casepd['url'].values:
                    repeatFlag=True
                    break
                case_list.append(case_title)
            if repeatFlag:break
        if len(case_list)>0 : #有更新数据才进行保存
            casepd=pandas.DataFrame(case_list)
            if len(self.casepd)>0:
                self.casepd=self.casepd.append(casepd,ignore_index=True)
            else:
                self.casepd=casepd
            self.casepd.to_csv('./resources/case_list.csv')

    def getCaseHtmlDetail(self):
        #取得内容
        URL = 'http://www.bjcourt.gov.cn'
        case_types=[]
        cause_types=[]
        doc_types=[]
        case_codes=[]
        case_contents=[]
        case_dates=[]
        for i in range(len(self.casepd)):
            #太快了之后会出现3XX，有一定的防刷
            time.sleep(5)
            url=URL+self.casepd.loc[i]['url']
            html = request.urlopen(url).read().decode('utf-8').replace('&nbsp;', '')
            selector = etree.HTML(html)
            #这是上框结构化数据，包括案件类型、案由、文档类型、案号、判决日期
            case_infos_=selector.xpath('//div[@class="fd-article-infor"]//td/input')
            case_types.append(case_infos_[1].attrib['value'])
            cause_types.append(case_infos_[2].attrib['value'])
            doc_types.append(case_infos_[3].attrib['value'])
            case_codes.append(case_infos_[4].attrib['value'])
            case_dates.append(case_infos_[5].attrib['value'])

            #这里把结果放到了script中，并进行了编码
            print(i)
            # print(execjs.get().name)
            script=selector.xpath('//div[@class="article_con"]/script/text()')[0].strip()[len('document.getElementById("cc").innerHTML = unescape("'):-3]
            script = script.encode('utf-8').decode('unicode_escape').encode('utf-8').decode('utf-8')
            neirong_re = re.search(
                "punctuation'>(.*)</body>", script,
                re.I | re.DOTALL)

            text = neirong_re.group(1)
            #去掉所有HTML标签
            text = re.sub('</?\w+[^>]*>', '', text).strip()
            #去掉所有空格
            text = re.sub(' ', '', text).strip()
            case_contents.append(text)
        if len(case_contents)>0:
            self.casepd['case_type']=case_types
            self.casepd['cause_type'] = cause_types
            self.casepd['doc_type'] = doc_types
            self.casepd['case_code'] = case_codes
            self.casepd['case_content'] = case_contents
            self.casepd['case_date']=case_dates
            self.casepd.to_csv('./resources/case_detail_list.csv')
            # self.casepd.to_csv('./resources/case_list.csv')

    #处理案件
    def executeCases(self):
        #补充其它字段
        claimants=[]
        respondents=[]
        results=[]
        judges=[]
        execMoneys=[]
        exeds=[]
        relateCases=[]
        for i in range(len(self.casepd)):
            html=self.casepd.loc[i]['case_content']
            sents, parseDependency=self.getSents(html,False)
            caseinfo = self.getCaseInfo(sents, parseDependency,dict(self.casepd.loc[i]))
            print(i)
            # pprint.pprint(caseinfo)
            # pprint.pprint(self.casepd.loc[i])
            claimants.append(','.join(caseinfo.get('申请执行人',[])))
            respondents.append(','.join(caseinfo.get('被执行人',[])))
            results.append(','.join( sorted(set(caseinfo.get('结果类型',[])))))
            judges.append(','.join(caseinfo.get('审判员', [])))
            maxmoney=caseinfo.get('标的', [0])
            execMoneys.append(max([float(n) for n in maxmoney]))
            exed = caseinfo.get('执行到位', [0])
            exeds.append(sum([float(n) for n in exed]))
            relateCases.append(','.join( sorted(set(caseinfo.get('关联案号',[])))))
        self.casepd['claimant']=claimants
        self.casepd['respondent'] = respondents
        self.casepd['result'] = results
        self.casepd['judge'] = judges
        self.casepd['money'] = execMoneys
        self.casepd['exed'] = exeds
        self.casepd['relateCases'] = relateCases

        self.casepd.to_csv('./resources/case_exe_list.csv')
        self.meta_company.to_csv('./resources/company_list.csv')
        # pprint.pprint(respondents)
        # a=pandas.DataFrame({'respondent':respondents})
        # a.to_csv('./resources/a.csv')
        # b=pandas.read_csv('./resources/a.csv',index_col=0)
        # print(list(b.loc[0]))
        # writer = pandas.ExcelWriter('./resources/a.xlsx')
        # a.to_excel(writer)
        # writer.save()
        # pprint.pprint(a)




if __name__=='__main__':
    filepath='./resources/wenshusample.txt'
    text=open(filepath, 'r', encoding='utf-8').read(-1)

    wenshu=Wenshu()
    #此结果应该进行缓存或保存，特别是如果出现一样的句子，不需要再次进行解析，而是从这里取得
    # sents,pd=wenshu.getSents(text)
    # caseinfo=wenshu.getCaseInfo(sents,pd)
    # pprint.pprint(caseinfo)
    # import chinese2digits as c2d
    #
    # print(c2d.takeNumberFromString('2、支付房屋使用费（二〇一三年二月一日至二〇一八年六月五日）三十万元等款项。11,333.22'))
    # x=takingChineseDigitsMixRERules.match('2、支付房屋使用费（二〇一三年二月一日至二〇一八年六月五日）三十万元等款项。')
    m=re.search('(?:支付|给付|^(?:(?!未).)*执行到位).*?((?:[一二三四五六七八九十千万亿兆幺零百]+(?:点[一二三四五六七八九幺零]+){0,1})|\d+(?:[\.,，]\d+)*万?)元',
                '一、唐山金信新能源有限公司于二〇一九年十二月三十日前给付李淑霞借款本金一万三千五百元及利息（以未还借款本金为基数，自二〇一八年六月七日起至欠款全部付清之日止，按照年利率21 % 计算利息）')
    #              '申请执行人于2020年4月13日依法向本院申请执行，经审查查明，张杰与金粤幕墙公司劳动争议一案，本院于2018年10月24日作出（2018）京0105民初92991号民事调解书，确认：一、原告金粤幕墙公司向被告张杰支付工资30,242.27元（于二〇一八年十二月三十一日前一次性支付10,000元，余款于二〇一九年六月三十日前一次性支付完毕），负担案件受理费9743元及公告费560元。被执行人依法应承担执行费8342元')
    print(m.group(1))

    # wenshu.getCaseHTML()

    # wenshu.getCaseHtmlDetail()

    wenshu.executeCases()
    pandas.read_csv('./resources/case_exe_list.csv',index_col=0).to_excel('./resources/case.xlsx')
    pandas.DataFrame(wenshu.moneysent).to_csv('./resources/moneysent.csv')
    print(len(wenshu.casepd))
