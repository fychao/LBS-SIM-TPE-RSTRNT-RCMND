#!/usr/bin/env python
# -*- coding:utf8 =*-
import re, logging, math, operator, gc, os
from zpickle import zloads, zdumps
import zlib, cPickle
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S')

def _zdumps(obj):
    return zlib.compress(cPickle.dumps(obj,cPickle.HIGHEST_PROTOCOL),9)

def _zloads(zstr):
    return cPickle.loads(zlib.decompress(zstr))  

def zdumps(obj, fn):
    return open(fn, "w").write(_zdumps(obj)) 

def zloads(fn):
    return _zloads(open(fn, "r").read())


class chilin:
    data = {}
    rdata = {}
    tagged = {}
    data_fn  = './zobj/chilin_data.obj'
    rdata_fn  = './zobj/chilin_rdata.obj'
    meta_fn   = './zobj/chilin_meta.obj'
    tagged_fn = './zobj/chilin_tagged.obj'
    meta = {}


    def __init__(self):
        self.load_obj()
        """ 這個函式會用到 Sinica """
        #self.init()


    def init(self):
        self.load_cnt()

    def getMeta(self, head):
        if head in self.meta.keys():
            return self.meta[head].strip()
        else:
            1
            #print "wrd:", head
            return head

    def getWordTagged(self, head):
        if self.tagged.has_key(head) and len(self.tagged[head])>0:
            return list(set(self.tagged[head]))

    def load_obj(self):
        self.meta = zloads(self.meta_fn)
        logging.info("[LOAD] %s load done! number: %d"%(self.meta_fn, len(self.meta)))
        self.data = zloads(self.data_fn)
        logging.info("[LOAD] %s load done! number: %d"%(self.data_fn, len(self.data)))
        self.rdata = zloads(self.rdata_fn)
        logging.info("[LOAD] %s load done! number: %d"%(self.rdata_fn, len(self.rdata)))
        self.tagged = zloads(self.tagged_fn)
        logging.info("[LOAD] %s load done! number: %d"%(self.tagged_fn, len(self.tagged)))

    def getHeadMeta(self, wrd):
        if self.rdata.has_key(wrd):
            return [self.getMeta(x[:4]) for x in self.rdata[wrd]]

    def getHead(self, wrd, mlen=4, head_only=set(['D', 'E', 'F', 'G', 'H', 'I']) ):
        if self.rdata.has_key(wrd):
            return [ x[:mlen] for x in self.rdata[wrd] if x[0] in head_only]

    def getWrd(self, head):
        if self.data.has_key(head):
            return self.data[head]

    def getAllinHead(self, code=True, head="A"):

        results = []
        for dkey in self.data.keys():
            if re.search("^%s"%(head), dkey):
                if code:
                    results.append( dkey )
                else:
                    results.append( self.getMeta(dkey[:2]) )

        return list(set(results))

if __name__ == "__main__":
    m_chilin = chilin()

    print m_chilin.getMeta('La')
    print "!!", m_chilin.getHead('群體')
    print '群體:', " ".join(m_chilin.getHeadMeta('群體'))
    print " ".join(m_chilin.getAllinHead(code=False))
    print " ".join(  m_chilin.getWrd("Je10B01=") )
    print " ".join(  m_chilin.getWordTagged("Je10B01=") )

    # logging.info("~~~~ [THE END]~~~~")
