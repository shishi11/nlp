from bert_serving.client import BertClient
from flask import Flask, Blueprint, request, jsonify, make_response, json, Response

from goldensents import GoldenSent
from ninteenth import sentenceParser
main=Blueprint('main',__name__)

@main.route('/')
def v_index():
    # request.path
    # app.sentenceParser.getSimilray2
    if request.method=='GET':
        content=request.args.get('content')
        if content==None:return 'None'
        # encode=app.sentenceParser.bc.encode([content])[0]
        orgs,distance=app.sentenceParser.getSimilray2(content)

        result=jsonify({'code':200,"results":{'orgs':orgs,'distance':distance}})
        rsp=make_response(result,200,{'Content-Type':'application/json'})
        rsp.headers['Access-Control-Allow-Origin']='*'

    return rsp

@main.route('/find')
def v1_index():
    if request.method=='GET':
        content=request.args.get('content')
        if content==None:return 'None'
        # encode=app.sentenceParser.bc.encode([content])[0]
        result=app.sentenceParser.find_19th_org(content)

        result=jsonify({'code':200,"results":result})
        rsp=make_response(result,200,{'Content-Type':'application/json'})
        rsp.headers['Access-Control-Allow-Origin']='*'

    return rsp
@main.route('/video/<file>')
def video(file):
    def generate():
        path='./video/'+file
        with open(path,'rb') as video:
            data=video.read(1024)
            while data:
                yield data
                data=video.read(1024)
    return Response(generate(),mimetype="video/mp4")

@main.route('/findGolden')
def v2_index():
    if request.method=='GET':
        content=request.args.get('content')
        if content==None:return 'None'
        # encode=app.sentenceParser.bc.encode([content])[0]
        result=app.golden.find_golden_org(content)

        result=jsonify({'code':200,"results":result})
        rsp=make_response(result,200,{'Content-Type':'application/json'})
        rsp.headers['Access-Control-Allow-Origin']='*'

    return rsp

app = Flask(__name__)
app.register_blueprint(main,url_prefix='/')


def prepare():
    # app.bc = BertClient(ip='192.168.1.103')
    # fin = open('./resources/ninteenth_sents.txt', 'r', encoding='UTF-8')
    #
    # app.lines = fin.readlines()
    # app.annoyIndex = AnnoyIndex(768)
    # app.annoyIndex.load('./mod/annoy_19th.model')
    app.sentenceParser=sentenceParser()
    app.golden=GoldenSent()


if __name__=='__main__':
    prepare()
    app.run(host='192.168.1.103')
