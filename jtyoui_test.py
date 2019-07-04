import pprint

from jtyoui import BaiDuInfoSearch

bd = BaiDuInfoSearch('汪洋')
print(bd.desc())
pprint.pprint(bd.info())
