import pickle
import re
import time

import pymysql
import requests
import json
import logging
from collections import defaultdict
import textProcess

logging.basicConfig(level=logging.INFO)  # ,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging = logging.getLogger(__name__)


class GeoKG():
    url = 'http://10.122.141.12:9006/similar'

    def get_sim(self, something):

        r = requests.post(self.url, json={"ck": "synonym", "synonym_word": something, "synonym_selectedMode": "auto",
                                          "homoionym_word": "", "homoionym_selectedMode": "auto", "homoionym_num": ""})
        json = r.json()
        result = []

        result = json['detail']['res']['synonym']
        return result

    def parseDoc(self, doc, threshold=1):  # 给一个阀值，当超过多少之后才认为有效。
        t=time.time()
        nslist = self.tp.posseg(doc, ['ns'])
        logging.info('%d nslist:%s' % (time.time()-t,str(nslist)))
        citylist = []
        districtlist = []
        provincelist = []
        citylist_ = []
        provincelist_ = []
        for ns in nslist:

            # if len(ns) > 1:
            # city, district, province,city_,province_ = self.getPlace(ns)
            # else:continue
            # if city: citylist.append(city['name'])
            # if district: districtlist.append(district['name'])
            # if province: provincelist.append(province['name'])
            # if city_: citylist_.append(city_['name'])
            # if province_: provincelist_.append(province_['name'])
            # if city: citylist.append(city)
            # if district: districtlist.append(district)
            # if province: provincelist.append(province)
            # if city_: citylist_.append(city_)
            # if province_: provincelist_.append(province_)
            if (self.city_dict.get(ns)):
                samename = self.city_dict.get(ns)
                for c in samename:
                    city = self.city_index.get(c['id'])
                    citylist.append(city)
                    # 补充上层地区
                    province_ = self.province_index.get(city['pid'])
                    provincelist_.append(province_)

            if (self.district_dict.get(ns)):
                samename = self.district_dict.get(ns)
                for d in samename:
                    district = self.district_index.get(d['id'])
                    districtlist.append(district)
                    city_ = self.city_index.get(district['pid'])
                    citylist_.append(city_)
                    province_ = self.province_index.get(city_['pid'])
                    provincelist_.append(province_)

            if (self.province_dict.get(ns)):
                samename = self.province_dict.get(ns)
                for p in samename:
                    province = self.province_index.get(p['id'])
                    provincelist.append(province)

        return self.filter_ai(provincelist,districtlist,citylist,provincelist_,citylist_)

    def filter_ai(self, provincelist, districtlist, citylist,provincelist_,citylist_,threshlod=1):
        # 如何根据地理关系，对位置进行过滤呢？
        # 1.如果d的上级有明确的C，则d和c都可以确认 ok
        # 2.如果c的上级有明确的P，则c和p都可以确认 ok
        # 3.如果只有一个明确的d，且没有非明确的其他的c，d被取消
        # 4.如果只有一个明确的c，且没有非明确的其他的p，也没有非明确同一个c ，c被取消
        # 5.如果有多个不同的d，指向同一个非确定c，则d和c都可确认ok
        # 6.如果有多个明确的c，指向同一个非确定的p，则c和p都可以确认。ok
        # 7.如果只有多个相同的d，？？？？？非确认
        # 8.如果只有多个相同的确认的c，？？？？非确认
        # 9.多个相同的确认的p，可确认p
        #10.如果d的c的p是确认的，中间没有明确的c，只有一个d，就只能确认，有多个d,但只有一个这样的d，不能确认

        # from collections import Counter
        # d_count = dict(Counter(districtlist))
        # c_count=dict(Counter(citylist))
        # for d in d_count:
        #     d2c=city_ = self.city_index.get(self.district_index.get())
        districtlist_sure=set()
        citylist_sure = set()
        provincelist_sure = set()

        for d in districtlist:
            d2c=self.city_index.get(d['pid'])
            if d2c in citylist:
                districtlist_sure.add(d['name'])
                citylist_sure.add(d2c['name'])
                continue
            if citylist_.count(d2c)>threshlod and districtlist.count(d)<citylist_.count(d2c):
                districtlist_sure.add(d['name'])
                citylist_sure.add(d2c['name'])
                citylist.append(d2c)#加到明确的c列表
                continue
            # c2p=self.province_index.get(d2c['pid'])
            if districtlist.count(d)==len(districtlist) and len(citylist)==0:
                districtlist_sure.add(d['name'])
                citylist_sure.add(d2c['name'])
                citylist.append(d2c)  # 加到明确的c列表


        for c in citylist:
            c2p=self.province_index.get(c['pid'])
            if c2p in provincelist:
                citylist_sure.add(c['name'])
                provincelist_sure.add(c2p['name'])
                continue
            if provincelist_.count(c2p)>threshlod and citylist.count(c)<provincelist_.count(c2p):
                citylist_sure.add(c['name'])
                provincelist_sure.add(c2p['name'])
                provincelist.append(c2p)
                continue
            if citylist.count(c)==len(citylist) and len(provincelist)==0:
                citylist_sure.add(c['name'])
                provincelist_sure.add(c2p['name'])
                provincelist.append(c2p)
                continue
        for p in provincelist:
            #只提到省
            if provincelist.count(p) == len(provincelist):
                provincelist_sure.add(p['name'])
                continue
            if provincelist.count(p)>threshlod:
                provincelist_sure.add(p['name'])


        # logging.info(str(districtlist_sure))
        # logging.info(str(citylist_sure))
        # logging.info(str(provincelist_sure))

        return citylist_sure,districtlist_sure,provincelist_sure


    # 暂时没有国的
    def getPlace(self, s, complete=True):
        city, district, province,city_,province_ = None, None, None,None,None
        if (self.city_dict.get(s)):
            # print('find city ', self.city_dict.get(s, set()))
            # print(self.city_index.get(self.city_dict.get(s, set())['id']))
            samename=self.city_dict.get(s)
            for c in samename:
                city = self.city_index.get(c['id'])
            # 补充上层地区
            if complete and city:
                province_ = self.province_index.get(city['pid'])

        if (self.district_dict.get(s)):
            # print('find district ', self.district_dict.get(s, set()))
            # print(self.district_index.get(self.district_dict.get(s, set())['id']))
            district = self.district_index.get(self.district_dict.get(s, set())['id'])
            if complete and district:
                city_ = self.city_index.get(district['pid'])

                province_ = self.province_index.get(city_['pid'])


        if (self.province_dict.get(s)):
            # print('find province ', self.province_dict.get(s, set()))
            # print(self.province_index.get(self.province_dict.get(s, set())['id']))
            province = self.province_index.get(self.province_dict.get(s, set())['id'])
        return city, district, province,city_,province_

    def test(self):
        # print(self.get_sim('本拉登'))
        s = '习近平在重庆调研时强调，创新、协调、绿色、开放、共享的发展理念，一带一路是在深刻总结国内外发展经验教训、分析国内外发展大势的基础上形成的，凝聚着对经济社会发展规律的深入思考，体现了“十三五”乃至更长时期我国的发展思路、发展方向、发展着力点。'
        s = '宝塔区冯庄乡康坪村是中国新民主主义青年团第一个农村团支部的诞生地。从2016年开始，康坪村办起了干部教育培训基地，同时农耕体验、采摘观光、窑洞民宿等多种旅游项目齐头并进。村里2015年建档立卡的30多户贫困户，去年已全部脱贫。'
        s = '5月的延安山青天蓝，游人如织。刚刚过去的“五一”假期，延安共接待游客255万多人次，同比增长29.6%。近年来，在红色旅游快速发展的带动下，延安依靠独特的历史人文和自然资源魅力，创建全域旅游城市，旅游产业成为延安打赢脱贫攻坚战的强劲推动力。\
　　黄河沿岸的千山万壑造就了延安市延川县雄奇的自然景观，位于县城以南48公里的乾坤湾镇，拥有红军东征革命纪念馆、黄河乾坤湾、伏羲码头等旅游资源。\
　　62岁的冯永泽经历过两次手术，身体一直不太好，曾长期靠低保和种枣树维持生活，4个子女都在外地打工，没法儿照顾老两口。\
　　2015年，认定为贫困户的冯永泽被招聘到乾坤湾镇黄河蛇曲国家地质公园做保洁员，每个月有1260元工资。老伴则用政府补助的5万元，在村里开起了农家乐，老两口每年的收入将近3万元。家里脱了贫，冯永泽越来越开朗。\
　　宝塔区冯庄乡康坪村是中国新民主主义青年团第一个农村团支部的诞生地。从2016年开始，康坪村办起了干部教育培训基地，同时农耕体验、采摘观光、窑洞民宿等多种旅游项目齐头并进。村里2015年建档立卡的30多户贫困户，去年已全部脱贫。\
　　2018年，康坪村引进专业的旅游公司，将村民闲置的窑洞打造成民宿，每孔窑洞每个月由企业支付200元，闲置窑洞变成了“乡村致富宝”。去年村里的民宿共接待游客3.2万人次。\
　　为了接待游客，村里把几孔窑洞改为能同时容纳100多人就餐的特色餐厅。去年，34岁的黄燕娃被招聘在餐厅厨房工作，每月工资2600元。\
　　黄燕娃说，村里发展民宿，把自己家的4孔窑洞出租了，随后又在餐厅找到工作。“去年还啥也不会做呢，现在有了做小吃的手艺，今后也不担心生活出路了。”\
　　洛川县是我国苹果主产区之一，还是著名的洛川会议旧址所在地。临近洛川会议纪念馆的阿寺村，在苹果种植业之外，依托红色旅游资源，发展特色农业休闲观光旅游，让群众脱贫致富又多一个途径。\
　　作为陕北苹果的发源地，永乡镇阿寺村如今除了有好吃的苹果，还变得更加好看好玩，村里墙上的农民画、街口的铜像都是以苹果为主题，每条小巷也都以不同的苹果品种命名，颇具特色。\
　　村里的主干道两边有店铺营业，接待各地游客。村民李磊磊的小超市就开在这条街上。26岁的他几年前不幸因车祸致残而失去了劳动能力。结婚不久、家里没什么积蓄的李磊磊，为了治疗费用，东拼西凑借了二十几万元，生活陷入困境。\
　　2017年被列为建档立卡贫困户后，李磊磊用政府发放的产业补助6000元，在村里开了个小超市。他通过在网上进货，小超市有了100多种日用品，也在一年的时间里为家里带来1万多元的纯收入。现在，李磊磊靠自食其力走出了阴影。\
　　“去年一年村里的旅游人次保守估计有10万，我们目前还在争创4A级景区，希望能吸引更多游客。”阿寺村驻村干部田林说。\
　　据延安市旅游局统计，2018年全市接待游客6343.98万人次，旅游综合收入410.7亿元。'
#         s='宝塔区冯庄乡康坪村是中国新民主主义青年团第一个农村团支部的诞生地。从2016年开始，康坪村办起了干部教育培训基地，同时农耕体验、采摘观光、窑洞民宿等多种旅游项目齐头并进。村里2015年建档立卡的30多户贫困户，去年已全部脱贫。\
# 　　2018年，康坪村引进专业的旅游公司，将村民闲置的窑洞打造成民宿，每孔窑洞每个月由企业支付200元，闲置窑洞变成了“乡村致富宝”。去年村里的民宿共接待游客3.2万人次。\
# 　　为了接待游客，村里把几孔窑洞改为能同时容纳100多人就餐的特色餐厅。去年，34岁的黄燕娃被招聘在餐厅厨房工作，每月工资2600元。\
# 　　黄燕娃说，村里发展民宿，把自己家的4孔窑洞出租了，随后又在餐厅找到工作。“去年还啥也不会做呢，现在有了做小吃的手艺，今后也不担心生活出路了。”\
# 　　洛川县是我国苹果主产区之一，还是著名的洛川会议旧址所在地。临近洛川会议纪念馆的阿寺村，在苹果种植业之外，依托红色旅游资源，发展特色农业休闲观光旅游，让群众脱贫致富又多一个途径。\
# 　　作为陕北苹果的发源地，永乡镇阿寺村如今除了有好吃的苹果，还变得更加好看好玩，村里墙上的农民画、街口的铜像都是以苹果为主题，每条小巷也都以不同的苹果品种命名，颇具特色。\
# 　　村里的主干道两边有店铺营业，接待各地游客。'
#         print(self.parseDoc(s))
#         s='新华社印务网“凹凸设计奖”报名入口开通诚邀全球设计师 中国财富网讯“凹凸设计奖”将于3月17日-20日在广东佛山举办的第十六届中博会国际家具展、中国（广东）国际定制家具博览会上发布。“凹凸设计奖”致力\
# 于搭建开源的全球设计师共享平台，通过设计驱动、产业融合、模式创新，实现全球原创设计智力资源的共享机制，让设计、生产、消费资源全球共享。“凹凸”是中国文字，也是世界符号。“凹凸”既蕴含着中国传统文化，又体现出了\
# 现代设计元素。“凹凸”师法自然，融汇着东方智慧和匠心精神，所以“凹凸”是无极限的。“凹凸设计奖”将采取面向社会公开发布和通过大赛组委会特邀导师进行定向提名推荐的双重方式共同邀请参赛者。   “凹凸设计奖”的参\
# 选对象为致力于“美好生活”的九大领域的全球设计师。评选工作由中华全国工商业联合会家具装饰业商会作为主要发起人，成立评奖委员会。首届评奖委员会由40位推荐导师、20位初审评委和5位终审评委共同构成。“凹凸设计奖”首\
# 创“导师制”赛制规则，大赛组委会将邀请40位世界著名设计师担任大赛导师，每位导师可推荐5位设计师。由导师对参赛者进行甄选、创意辅导、参赛指导，以及未来导师工作室的设计定向培养签约合作等。该赛制模式将为“凹凸设计\
# 奖”进行赛事质量把关及后续市场推广合作产生可持续的商业动能。导师们将在第十六届中博会国际家具展开幕仪式上共同宣言，并将受邀签约入驻“国际贸易设计中心（家居）”，为促进服务贸易创新设计领域的国际合作走出一条创新\
# 之路。2018年11月，首个面向家居行业设计服务的国际贸易平台落户上海普陀区月星家居茂。图为国际贸易设计中心（家居）揭牌仪式附：1.“凹凸设计奖”的申报条件申报对象为全球设计师。申报作品必须是原创作品，其形式包括概念\
# 设计、产品和创新服务，作品版权所有人可为最终获得知识产权的个人、组织、团队或公司。还未申请取得“知识产权”，但确保符合原创设计的作品也可申报。申报作品分为家具设计、室内设计、软装陈设、家居饰品、智能科技、灯光\
# 设计、艺术装置、展览展示、材料应用九大类，寓意“打开美好生活的九种方式”。2.凹凸设计奖”的申报流程申报渠道：（1）组委会特邀导师推荐 （2）大赛官网：www.aotuaward.com申报作品展示日期：2019年3月17日-20日展示地\
# 点：第十六届中博会国际家具展中国（广东）国际定制家具博览会申报截止日期：2019年6月30日。申报入口：http://aotuaward.yuexing.com（申报为在线申报，按申报表条件和要求填写及上传资料。）评审委员会依据本办法规定的申\
# 报条件和要求对申报的作品进行初评，并将初审结果告知申报人或申报单位，并进入终评。评审结果在2019年7月公布。'
        #两个普陀区的问题，一个在舟山，一个在上海
        # print(self.parseDoc(s))
        rows=self.query_city_name('select site_name,txt from e20190303 limit 10')
        for row in rows:
            title=row[0]
            detail=row[1]
            logging.info(title+detail)
            t=time.time()
            cl,dl,pl=self.parseDoc(title+detail)
            logging.info('%s %s %s' %(str(dl),str(cl),str(pl)))
            logging.info('cost:%d' %(time.time()-t))
            logging.info('-'*15)


    def connect_db(self):
        return pymysql.connect(host='192.168.1.101',
                               port=3306,
                               user='root',
                               password='',
                               database='xinhua',
                               charset='utf8')

    def query_city_name(self, sql_str):
        # sql_str = ("%s" % cc
        #            )
        logging.info(sql_str)

        con = self.connect_db()
        cur = con.cursor()
        cur.execute(sql_str)
        rows = cur.fetchall()
        cur.close()
        con.close()

        # assert len(rows) == 1, 'Fatal error: country_code does not exists!'
        return rows

    def __init__(self):

        load_file = open('./mod/city_dict.bin', 'rb')
        self.city_dict = pickle.load(load_file)
        load_file = open('./mod/city_index.bin', 'rb')
        self.city_index = pickle.load(load_file)
        logging.info('city count %d,city name count:%s' % (len(self.city_index), len(self.city_dict)))

        load_file = open('./mod/district_dict.bin', 'rb')
        self.district_dict = pickle.load(load_file)
        load_file = open('./mod/district_index.bin', 'rb')
        self.district_index = pickle.load(load_file)
        logging.info('district count %d,district name count:%s' % (len(self.district_index), len(self.district_dict)))

        load_file = open('./mod/province_dict.bin', 'rb')
        self.province_dict = pickle.load(load_file)
        load_file = open('./mod/province_index.bin', 'rb')
        self.province_index = pickle.load(load_file)
        #这里还应该去掉一些错的。

        logging.info('province count %d,province name count:%s' % (len(self.province_index), len(self.province_dict)))

        self.tp = textProcess.TextProcess()

    def genCity(self, cities):
        #字典模式下，如果出现重复就没法处理了，怎么办呢？
        # from collections import

        cityName_all_dict = defaultdict(list)
        cityIndex = dict()
        # def addsame(cityName_all_dict,city):
        #     pid=[city[2]]
        #
        #     if cityName_all_dict.get(city[1]):
        #
        #         #如果有同名的
        #         pid=cityName_all_dict.get(city[1])['pid']
        #         pid.append(city[2])
        #
        #     return pid
        for city in cities:
            cityName = city[1]
            aliasCityName = self.get_sim(cityName)
            cityName_all = set([cityName]).union(set(aliasCityName))
            #这里是全的
            cityIndex[city[0]] = {'name': city[1], 'pid': city[2]}
            #这里开始有交叉
            # cityName_all_dict[city[1]].append({'id': city[0], 'pid': city[2]})
            # if cityName_all_dict.get(city[1]):
            #     #如果有同名的
            #     pid=cityName_all_dict.get(city[1])['pid']
            #     pid.append(city[2])
            #     cityName_all_dict[city[1]] = {'id': city[0], 'pid': pid}
            # else:
            #     cityName_all_dict[city[1]] = {'id': city[0], 'pid': [city[2]]}
            # cityName_all_dict[city[1]] = {'id': city[0], 'pid': addsame(cityName_all_dict,city[2])}

            if (city[1][-1] in ['市', '县', '省']):
                cityName_all.add(city[1][:-1])
                # cityName_all_dict[city[1][:-1]].append({'id': city[0], 'pid': city[2]})

            for c in cityName_all:
                cityName_all_dict[c].append({'id': city[0], 'pid': city[2]})
        print('city count %d,all_city count %d' % (len(cityIndex), len(cityName_all_dict)))
        return cityName_all_dict, cityIndex

    def gen(self):
        cities = self.query_city_name('SELECT CityID,CityName,ProvinceID FROM s_city')
        city_dict, city_index = self.genCity(cities)
        s_districtes = self.query_city_name('SELECT DistrictID,DistrictName,CityID FROM s_district')
        district_dict, district_index = self.genCity(s_districtes)
        s_provinces = self.query_city_name('SELECT ProvinceID,ProvinceName,Abbreviation FROM s_province')
        province_dict, province_index = self.genCity(s_provinces)

        fou = open('./mod/city_dict.bin', 'wb')
        pickle.dump(city_dict, fou)
        fou.close()
        fou = open('./mod/city_index.bin', 'wb')
        pickle.dump(city_index, fou)
        fou.close()
        fou = open('./mod/district_dict.bin', 'wb')
        pickle.dump(district_dict, fou)
        fou.close()
        fou = open('./mod/district_index.bin', 'wb')
        pickle.dump(district_index, fou)
        fou.close()
        fou = open('./mod/province_dict.bin', 'wb')
        pickle.dump(province_dict, fou)
        fou.close()
        fou = open('./mod/province_index.bin', 'wb')
        pickle.dump(province_index, fou)
        fou.close()


g = GeoKG()
# g.gen()
# s='习近平在重庆调研时强调，创新、协调、绿色、开放、共享的发展理念，一带一路是在深刻总结国内外发展经验教训、分析国内外发展大势的基础上形成的，凝聚着对经济社会发展规律的深入思考，体现了“十三五”乃至更长时期我国的发展思路、发展方向、发展着力点。'
# g.parseDoc(s)
g.test()