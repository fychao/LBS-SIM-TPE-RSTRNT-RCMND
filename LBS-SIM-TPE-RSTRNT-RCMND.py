#!/usr/bin/env python
# -*- coding:utf8 =*-
from zpickle import *
from bs4 import BeautifulSoup
import codecs, urllib
import re
import os
import os.path
import json
import math
import time
import collections
import operator
import random
import chilin
import math
from sinica import getPOS
from joblib import Parallel, delayed
from gensim import corpora, models, similarities
from pprint import pprint
from itertools import cycle
import pylab as pl
import numpy as np
import urlparse
import BaseHTTPServer
import SimpleHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
import jieba

# Chinese NLP

class zTags():
    ''' 所有的 POS TAG 元素 '''
    @staticmethod
    def getEol():
        EOLS = [
            "FW",
            "QUESTIONCATEGORY",
            "COLONCATEGORY",
            "COMMACATEGORY",
            "DASHCATEGORY",
            "ETCCATEGORY",
            "PARENTHESISCATEGORY",
            "PAUSECATEGORY",
            "PERIODCATEGORY",
            "QUESTIONCATEGORY",
            "SEMICOLONCATEGORY",
            "EXCLANATIONCATEGORY",
            "EXCLAMATIONCATEGORY",
            "BR",
            "SPCHANGECATEGORY"]
        return set(EOLS)
    
    @staticmethod
    def isEol(tag):
        EOLS = zTags.getEol()
        return True if tag in EOLS else False
        
    ''' 過濾出不要的標記 '''
    @staticmethod
    def isWant(tag):
        NOT_WANT = ["^P", "^C", "^D", "^N[c|d|e|f|g|h]", "V_2", "^T", "^SHI"]
        NOT_WANT.extend(zTags.getEol())
        flg = True
        NOT_WANT = set(NOT_WANT)
        for ele in NOT_WANT:
            if re.match(ele, tag):
                flg = False
        return flg
                
    @staticmethod
    def isNot(word):
        ''' 否定句 '''
        # "但是", "但", 
        NOTS = [u"不", u"沒有", u"不要", u"不能", u"沒", u"沒有", u"無", u"不會", u"難", u"算不上", u"未"]
        NOTS = set(NOTS)
        return True if word in NOTS else False
        
    @staticmethod
    def notMorph(word):
        '''帶否定語素'''
        NOTs = u"^[不|難|沒|未]"
        return re.sub(NOTs, "", word) if re.match(NOTs, word) else False

class zWord():
    ''' 基本單詞元素 '''
    def __init__(self, word, go_prev=None, go_next=None):
        self.org = word
        (word, tag) = zWord.toElements(word)
        self.word = word
        
        self.tag = tag
        
        ''' 設定 wanted '''
        self.wanted = zTags.isWant(tag)
        
        ''' 設定 ORI '''
        if zTags.isNot(self.word):
            self.ori = 0
            self.wanted = False
        else:
            self.ori = 1

        # 詞中有否定
        self._selfNot()
            
        # 取得最佳表達式
        self.word_best = self.get_best()

        
    def get_best(self):
        """
            取得最好的表達式， 例如： "不" -> ""； "不用" -> "用-"
        """
        if not self.wanted:
            # 詞類不要
            return ""
        if self.ori == 0:
            # 否定字組
            return ""
        
        return self.word.replace("-", "") if self.ori > 0 else self.word.replace("-", "")+u"-" 
    
    def _selfNot(self):
        '''詞中帶有否定'''
        if not zTags.isNot(self.word) and zTags.notMorph(self.word): # 要改這裡
            if not len(self.word) == 1: # 要改這裡
                '''多語素'''
                self.ori = 0
                # 帶"不"頭
                self.word = zTags.notMorph(self.word)
                self.wanted = True
            else:
                '''單語素'''
                self.ori = 0
                self.word = ""
                self.wanted = False
        
    ''' Toggle Negative '''
    def toggle(self):
        if self.ori == 1:
            self.ori =-1 
        elif self.ori ==-1:
            self.ori = 1 
        
        
    ''' 分開 tag 與 word '''
    @staticmethod
    def toElements(word):
        eles = word.replace(u")", u"").split(u"(")
        if len(eles)==2:
            return (eles[0], eles[1])
        
    def __str__(self):
        return "[%s] %s(%s:%s:%s)"%(self.__class__.__name__, 
                              self.word_best.encode("utf8"),
                              self.tag.encode("utf8"),
                              self.ori,
                              self.wanted
                              )


class zSentence:
    ''' NOTE: 引入的 stn 一定要先用 toWords 切開
        單句元素，會包 zWord 
    '''
    def __init__(self, stn):
        if type(stn)==type([]):
            self.stn_org = stn
        if type(stn)==type(u""):
            self.stn_org = zSentence.toWords(stn)
        self.proc()

    """ 處理評論句子內容 """
    def proc(self):
        words = []
        
        for word in self.stn_org:
            words.append( zWord(word) )
            
        self.words = words
        
        self.notOperation()
        
    def get_words(self):
        return [ wrd for wrd in self.words] 
    
    def get_wanted(self):
        ''' 取得需要的字元 '''
        return [ wrd for wrd in self.words if wrd.wanted]
        
    def notOperation(self):
        """ 否定句處理 """
        for idx in range(len(self.words)):
            if self.words[idx].ori == 0:
                for idy in range(idx, len(self.words)):
                    self.words[idy].toggle()
    
    def __str__(self):
        return "[%s] Words:%s"%(self.__class__.__name__, len(self.words)) 
        
    @staticmethod
    def toWords(stn):
        ''' 開成字段 '''
        if re.search(u"　", stn):
            return stn.split(u"　")
        if re.search(u" ", stn):
            return stn.split(u" ")
      
    @staticmethod
    def skipWindow(seq, max_win=5):
        """
            SKIP Window 算法
        """
        olen = len(seq)
        rterms = []
        for pivot in range(olen):
            left  = (pivot - max_win) if (pivot - max_win) > 0 else 0
            right = (pivot + max_win) if (pivot + max_win) < olen else olen

            for idx in range(left, right):
                if not idx == pivot and (seq[pivot].wanted and seq[idx].wanted):
                    """ 回傳組合，不從順序，從筆劃 """
                    if len(seq[pivot].word[0]) > 0 and len(seq[idx].word[0]) > 0:
                        if seq[pivot].word[0] > seq[idx].word[0]:
                            rterms.append( ( seq[pivot], seq[idx] ) ) 
                        else:
                            rterms.append( ( seq[idx], seq[pivot] ) ) 

        return set(rterms)

class zOpinion:
    """ 單一評論 """
    def __init__(self, opn):
        self.data = opn
        self.stns = []
        self.word_only = []
        self.proc()
        
    """ 處理評論內容 """
    def proc(self):
        stns = zOpinion.toStn(self.data)
        for stn in stns:
            self.stns.append(zSentence(stn))
            
        self.stat()
        self._doWords4Tag()
        
    """ 評論內的字數統計 """
    def stat(self):
        
        ''' 單一詞統計 '''
        oWords = []
        
        ''' bigram 統計 '''
        oBigrams = []
        oRadiBigrams = []
        for stn in self.stns:
            self.word_only.extend([x.word for x in stn.get_words()])
            oWords.extend([ x.word_best for x in stn.get_wanted()])
#             oBigrams.extend(stn.get_bigrams())
#             oRadiBigrams.extend([ (term2Radi(x), term2Radi(y)) for (x, y) in stn.get_bigrams()])
            
        # 單一詞結果
        self.stat_words = oWords
        self.stat_words_dic = collections.Counter(oWords)
        
        # 雙詞的結果
#         self.stat_bigrams = oBigrams
#         self.stat_bigrams_dic = collections.Counter(oBigrams)
        
        # 雙詞的部首
#         self.stat_radi_bigram = oRadiBigrams
        
    def getOrg(self):
        return self.data['tagged']
        
    """ 取得特定 key 的值 """
    def get(self, key):
        if key in self.getKeys():
            return self.data[key]
        
    def _doWords4Tag(self):
        wrds = []
        for stn in self.stns:
            for word in stn.get_wanted():
                wrds.append(word.get_best()) # here
        self._stn_words = wrds
#         self._stn_radical_pairs = [ term2Radi(x) for x in wrds]

    def getWords4Tag(self):
        return self._stn_words
    
    def getRadicalsPair4Tag(self):
        return self._stn_radical_pairs
    
    
    def __str__(self):
        return "[%s] words:%s"%(self.__class__.__name__, len(self.stat_words_dic.keys()))  

        
    def getPair(self, wanted_terms):
        """ 取得必要的 pair """

#         sorted2Terms = lambda x, y: (x, y) if x > y else (y, x)
#         isInBigram = lambda x,y: sorted2Terms(x,y) if sorted2Terms(x,y) in self.stat_bigrams_dic.keys() else False

        wanted_pairs = [ x for x in self.stat_bigrams_dic.keys() if x[0] in wanted_terms or x[1] in wanted_terms]

        return_pairs = []
        for stn in self.stns:
            stn_terms = list(set([ wrd.word_best for wrd in stn.get_wanted()]))
            for pair in wanted_pairs:
                size = len(set([ x.replace("-", "") for x in stn_terms]).intersection(set(pair)))
                if size >= 1:
                    org_x = "".join([ x for x in stn_terms if x.replace("-", "") == pair[0]])
                    org_y = "".join([ x for x in stn_terms if x.replace("-", "") == pair[1]])
                    return_pairs.append( "%s/%s"%(org_x, org_y) )
            
        return list(set(return_pairs))
    
    @staticmethod
    def toStn(stn):
        ''' 開成字段, [ [word, word], [] ... ] '''
        tagged = u"　 ".join(stn.split("\n"))
        words = zSentence.toWords(tagged)
        stns = []
        stn = []
        for idx in range(len(words)):
            ''' 可能會有空字串 '''
            try:
                (word, tag) = zWord.toElements(words[idx])
                stn.append(words[idx])
                if zTags.isEol(tag):
                    # 如果字串少於1 個字，就跳開
                    if len(stn) >1:
                        stns.append(stn)
                    stn = []
            except: 
                continue
        if len(stn) >1:
            stns.append(stn)

        return stns


oChi = chilin.chilin()

def cnv2chilin(wrd):
    ''' 使用詞林擴充 '''
    tobj = oChi.getHead(wrd.encode("utf8"), 8)
    if tobj:
        tobj = [ x for x in tobj if (not x[0] in ['A', 'C', 'J', 'K', 'L']) and not x[-1] in ['#']]
        if len(tobj)>0:
#             print wrd, " ".join(tobj)
            grps = [ [ y.decode("utf8") for y in oChi.getWrd(x)] for x in tobj ] 
            return set([item for sublist in grps for item in sublist]) # see http://bit.ly/1FrTjwF
        return set([wrd])
    else:
        return set([wrd])
    
def chilinExt(aSet):
    # 使用辭林擴充
    ext = set()

    if type(aSet) == type(set()):
        for x in aSet:
            flg = False
            if re.search("-$", x):
                flg = True

            cnvted = cnv2chilin(x.replace("-", ""))
            ext.update(["%s"%x if not flg else "%s-"%x for x in cnvted])
    elif type(aSet) == type(u""):
        flg = False
        if re.search("-$", aSet):
            flg = True
        cnvted = cnv2chilin(aSet.replace("-", ""))
        ext.update(["%s"%x if not flg else "%s-"%x for x in cnvted])
        
    return " ".join(ext).replace("-", u"負")

def getChilinTxt(tagged):
    opn = zOpinion(tagged)
    txts = Parallel(n_jobs=-1)(delayed(chilinExt)(set([x.get_best() for x in stn.get_wanted()])) for stn in opn.stns)
    return " ".join(txts)

def clnSinica(mstr):
#     print ">>", " ".join(re.findall(p, unicode(mstr.decode("utf8"))))
    mstr = mstr.replace('<?xml version="1.0" ?><wordsegmentation version="0.1"><processstatus code="0">Success</processstatus><result>', "")
    mstr = mstr.replace('</result></wordsegmentation>', "")
    mstr = mstr.replace('</sentence>', '')
    mstr = mstr.replace('<sentence>', '')
    return mstr

def clnTxt(mstr):
    return "".join([ x.split("(")[0] for x in mstr.strip().split(u"　") if len( x.split("(") ) >1])


def distance_on_unit_sphere(lat1, long1, lat2, long2):
    # 以 KM 回傳，原程式碼在 http://goo.gl/JExDdc
    # 回傳是公里
    # Convert latitude and longitude to 
    # spherical coordinates in radians.
    degrees_to_radians = math.pi/180.0
         
    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians
         
    # theta = longitude
    theta1 = long1*degrees_to_radians
    theta2 = long2*degrees_to_radians
         
    # Compute spherical distance from spherical coordinates.
         
    # For two locations in spherical coordinates 
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) = 
    #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length
     
    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + 
           math.cos(phi1)*math.cos(phi2))
    arc = math.acos( cos )
 
    # Remember to multiply arc by the radius of the earth 
    # in your favorite set of units to get length.
    return arc * 6373

def diff_lat_lon(me_loc, target):
    return distance_on_unit_sphere(float(me_loc['lat']), float(me_loc['lon']), 
                                   float(target['lat']), float(target['lon']))


distance_weight = lambda x: 1 if x <= float(1) else 0.9 if x <= float(2) else 0.8
rank_code = lambda x: "P" if int(x)>=45 else "N"

oCol = load("./zobj/Taipei_shops_comments.zobj")
print len(oCol)

## //1 build dictionary
#txts = [ ("%s %s"%( " ".join(x[0].values()), x[1])).split(" ") for x in oCol]
#dictionary = corpora.Dictionary(txts)
#dictionary.filter_tokens(bad_ids=[0])
#dictionary.filter_extremes(no_below=3)
#dictionary.compactify()
#dictionary.save("./zobj/16908_dictionary.mm")
#print len(dictionary.token2id)
#print "build dictionary ok!"
##raw_input("STOP!!!")


dictionary = corpora.Dictionary.load("./zobj/16908_dictionary.mm")
print len(dictionary.token2id)

#ntusd_hash = load("./zobj/NTUSD_HASH_POS_NEG.zobj")

txts_pos = load("./zobj/Taipei_shop_Txt_pos.zobj")
txts_neg = load("./zobj/Taipei_shop_Txt_neg.zobj")

#print "classify opinions"
#corpus_pos = [ dictionary.doc2bow(x[1].split(" ")) for x in txts_pos]
#corpus_neg = [ dictionary.doc2bow(x[1].split(" ")) for x in txts_neg]
#print "builded corpus_pos, corpus_neg:", len(corpus_pos), len(corpus_neg)

#corpora.MmCorpus.serialize('./zobj/Taipei_shop_corpus_pos.mm', corpus_pos)
#corpora.MmCorpus.serialize('./zobj/Taipei_shop_corpus_neg.mm', corpus_neg)
#print "saving corpus_pos, corpus_neg"


corpus_pos = corpora.MmCorpus('./zobj/Taipei_shop_corpus_pos.mm')
corpus_neg = corpora.MmCorpus('./zobj/Taipei_shop_corpus_neg.mm')
print "loading corpus_pos, corpus_neg:", len(corpus_pos), len(corpus_neg)

#print "build LSI model"
#tfidf_pos = models.TfidfModel(corpus_pos)
#lsi = models.LsiModel(tfidf_pos[corpus_pos], num_topics=200, id2word=dictionary)
#lsi.save('./zobj/Taipei_shops_LSI.index')
#print "build ok and saved!"

lsi = models.LsiModel.load('./zobj/Taipei_shops_LSI.index')
#print "\n".join(lsi.print_topics(10))

#print "building similarity index..."
#index = similarities.MatrixSimilarity(lsi[corpus_pos])
#index.save('./zobj/Taipei_shops_ALL_INDEX.index')
#print "build ok and save"


index = similarities.MatrixSimilarity.load('./zobj/Taipei_shops_ALL_INDEX.index')


def start_interactive(mstr = u"可以聊天，吃火鍋", me_loc = { 'lat': 25.041171, "lon":121.565227}, num=9):
    #tagged = clnSinica(getPOS(u"吃".encode("utf8")+mstr.encode("utf8")))
    #proc_txt = [ x.replace("-", u"負") for x in zOpinion(tagged.decode("utf8")).getWords4Tag()]

    tagged = jieba.cut(u"吃，".encode("utf8")+mstr.encode("utf8"), cut_all=False)
    tagged = " ".join([ "%s(NN)"%x for x in tagged ])
    print tagged
    proc_txt = [ x.replace("-", u"負") for x in zOpinion(tagged).getWords4Tag() if x not in set([u"餐廳", u"餐廳-"])]

    print " ".join(proc_txt)

    mstr_bow = dictionary.doc2bow(proc_txt)
    print mstr_bow
    vec_lsi = lsi[mstr_bow]
    sims = index[vec_lsi]

    shops_attr = {}
    shops_val = {}
    for (x,y) in sorted(enumerate(sims), key=lambda item: -item[1]):

        # 如果數值太小
        if y <= float(0.0000001):
            continue

        shop_name = txts_pos[x][0]['title']
        target = { 'lat': txts_pos[x][0]['latitude'], 'lon': txts_pos[x][0]['longitude'] }
    
        dist = diff_lat_lon(me_loc, target)
    
        if not shops_val.has_key(shop_name):
            shops_val[shop_name] = []
            shops_attr[shop_name] = txts_pos[x][0]
        shops_val[shop_name].append(distance_weight(dist)*y)
    

    shops_rcmd = {}    
    for shop_name in shops_val.keys():
        shops_rcmd[shop_name] = np.average(shops_val[shop_name])
    
    return_ans = []
    for x in sorted(shops_rcmd.items(), key=operator.itemgetter(1), reverse=True)[:num]:
        print "%s: %.4f"%(x[0], x[1])
        return_ans.append( ("-".join(x[0].split("-")[1:]), x[1], shops_attr[ x[0] ]) )

    return return_ans


class MyHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):

        # Parse query data & params to find out what was passed
        parsedParams = urlparse.urlparse(self.path)
        queryParsed = urlparse.parse_qs(parsedParams.query)
        print queryParsed

        # request is either for a file to be served up or our test
        if parsedParams.path == "/":
            SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self);
        elif parsedParams.path == "/rcmd":
            self.processMyRequest(queryParsed)
        else:
            # Default to serve up a local file 
            #SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self);
            self.send_response(404)



    def processMyRequest(self, query):
        is_json = True

        self.send_response(200)

        if is_json:
            self.send_header('Content-Type', 'application/json; charset=utf-8')
        else:
            self.send_header('Content-Type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        html_txt = ""
        if query.has_key('q'):
            query_q = "\n".join(query['q'])
            if query.has_key('loc_lat') and query.has_key('loc_lon'):
                loc_lat = float(query['loc_lat'][0])
                loc_lon = float(query['loc_lon'][0])
                print query_q, loc_lat, loc_lon
                html_txt = start_interactive(mstr = query_q.decode("utf8"), me_loc= { 'lat': loc_lat, "lon": loc_lon})
            else:
                print query_q
                html_txt = start_interactive(mstr = query_q.decode("utf8"))

        if is_json:
            json_txt = json.dumps(html_txt, sort_keys=True, indent=4, separators=(',', ': '), ensure_ascii=False, encoding="utf-8")
            self.wfile.write( codecs.encode(json_txt, ("utf8")) ) 
        else:
            self.wfile.write( html_txt ) 

        self.wfile.close();

if __name__== '__main__':
    print "boot ok!"

    HandlerClass = MyHandler
    ServerClass  = BaseHTTPServer.HTTPServer
    Protocol     = "HTTP/1.0"
    port         = 1863
    server_address = ('140.119.19.172', port)

    HandlerClass.protocol_version = Protocol
    httpd = ServerClass(server_address, HandlerClass)

    sa = httpd.socket.getsockname()
    print "Serving HTTP on", sa[0], "port", sa[1], "..."
    httpd.serve_forever()


