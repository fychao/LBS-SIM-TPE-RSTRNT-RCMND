#!/usr/bin/env python
# -*- coding:utf8 =*-
# modified at 2014-11-07, add recv_timeout for longer data return
# modified at 2013-10-14
import sys, cgi, os, time, urllib2, urllib, re, cookielib, random
from time import strftime, gmtime
from socket import *
from bs4 import BeautifulSoup 
from ConfigParser import SafeConfigParser

config = SafeConfigParser()
config.read("idpw.ini")
mid = config.get('SINICA', 'ID')
mpw = config.get('SINICA', 'PW')


def html_escape(text):
    text = text.replace('&', '&amp;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#39;')
    text = text.replace(">", '&gt;')
    text = text.replace("<", '&lt;')
    return text


def recv_timeout(the_socket,timeout=2):
    #make socket non blocking
    the_socket.setblocking(0)
    #total data partwise in an array
    total_data=[];
    data='';
    #beginning time
    begin=time.time()
    while 1:
        #if you got some data, then break after timeout
        if total_data and time.time()-begin > timeout:
            break
        #if you got no data at all, wait a little longer, twice the timeout
        elif time.time()-begin > timeout*2:
            break
        #recv something
        try:
            data = the_socket.recv(8192)
            if data:
                total_data.append(data)
                #change the beginning time for measurement
                begin=time.time()
            else:
                #sleep for sometime to indicate a gap
                time.sleep(0.1)
        except:
            pass
    #join all parts to make final string
    return ''.join(total_data)

def getPOS(mstr):
    # 下面是 parser 用 fychao1
    #serverHost = '140.109.19.112'       # servername is localhost
    #serverPort = 8000                   # use arbitrary port > 1024
    # 下面是 斷詞 用 fychao
    serverHost = '140.109.19.104'       # servername is localhost
    serverPort = 1501                   # use arbitrary port > 1024

    s = socket(AF_INET, SOCK_STREAM)    # create a TCP socket

    #template = open("template.xml", "r").read();
    template = '<?xml version="1.0" ?>' 
    template += '<wordsegmentation version="0.1">'
    template += '<option showcategory="1" />'
    template += "<authentication username=\"%s\" password=\"%s\" />"%(mid, mpw)
    template += '<text>%s</text>'
    template += '</wordsegmentation>'
    s.connect((serverHost, serverPort)) # connect to server on the port
    print template%mstr
    s.send(template%mstr.decode("utf8", 'ignore').encode("big5", 'ignore'))               # send the data
    #data = recv_timeout(s)
    data = s.recv(2*4096)                 # receive up to 1K bytes
    return data.decode("big5", 'ignore').encode("utf8")

proxy_support = urllib2.ProxyHandler({"http" : "http://127.0.0.1:3128"})
#proxy_support = urllib2.ProxyHandler({"http" : "http://163.28.32.102:3128"})
cj = cookielib.CookieJar()

def getHtml(url, query):
    global proxy_support, cj
    u = ''
    detail = ''
    while True:
        opener=urllib2.build_opener(urllib2.HTTPCookieProcessor(cj), proxy_support)
        #opener=urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        opener.addheaders = [('User-agent', 'Mozilla/5.0 (iPad; U; CPU OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B334b Safari/531.21.10')]
        urllib2.install_opener(opener)
        try:
            req=urllib2.Request(url, query)
            fetch_timeout = 25
            u=urllib2.urlopen(req, None, fetch_timeout)
            detail=u.read().decode("big5", 'ignore').encode("utf8")
        except Exception as e:
            t = random.randint(5,15)
            print type(e)
            print "Sinica >>> Sleep Start : %s + %s" % (strftime("%Y_%m_%d_%H_%M_%S", gmtime()), t)
            time.sleep( t )

        if len(detail) >10:
            break

    return detail


def getPOSweb(mstr):

    txt = ""
    while True:
        txt = _doPOSweb(mstr)
        if not re.search("503 Service Temporarily Unavailable", txt):
            break
        else:
            print "found HTTP code 503, try again!"

    return txt

def _doPOSweb(mstr):
    cj = cookielib.CookieJar()
    #proxy_support = urllib2.ProxyHandler({"http" : "http://163.28.32.102:3128"})
    #opener=urllib2.build_opener(urllib2.HTTPCookieProcessor(cj), proxy_support)
    opener=urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    opener.addheaders = [('User-agent', 'Mozilla/4.0 (compatible; MSIE 6.0; Windows 7)')]
    urllib2.install_opener(opener)

    data = urllib.urlencode([('query', mstr.decode("utf8", "ignore").encode("big5", "ignore"))])
    url="http://mt.iis.sinica.edu.tw/cgi-bin/text.cgi"
    html = getHtml( url, data)
    #req = urllib2.Request(url)
    #fd = urllib2.urlopen(req, data)
    html = html.split("\n")
    for line in html:
        if re.match('<META HTTP-EQUIV="REFRESH" CONTENT="0.1; URL=', line):
            url = "http://mt.iis.sinica.edu.tw"+re.sub('\'">', '', re.sub('<META HTTP-EQUIV="REFRESH" CONTENT="0.1; URL=\'', '', line))
            #detail = urllib.urlopen(url).read().decode("big5").encode("utf8")
            #detail = urllib.urlopen(url).read().decode("big5").encode("utf8")
            detail = getHtml(url, urllib.urlencode([]))
            detail = re.sub('<meta http-equiv=Content-Type content="text/html"; charset="UTF-8">', '', detail)
            detail = BeautifulSoup(detail)
            for tag_a in detail.findAll('a', href=re.compile("tag")):
                url = "http://mt.iis.sinica.edu.tw"+tag_a.attrs['href']
                tagged_data = re.sub("\n", "", urllib.urlopen(url).read().decode("big5").encode("utf8")).split("-"*130+"")

                output = ''
                for sentence in tagged_data:
                    if len(sentence)>2:
                        output += "<sentence>"+sentence+"</sentence>"
                return "<SINICA>%s</SINICA>"%output

def main():
    print "this is lib"
    print getPOS("你好嗎?")
'''
ex_dir = 'mobile01/'
tagged_dir = 'tagged/'
counter = 0
for dir in os.listdir(ex_dir):
    if not os.path.exists(tagged_dir+dir):
        os.makedirs(tagged_dir+dir)
    for s_dir in os.listdir( ex_dir+dir ):
        from_fn = ex_dir+dir+"/"+s_dir
        to_fn = tagged_dir+dir+"/"+s_dir
        if os.path.exists( to_fn ):
            continue
        if not os.path.isfile(to_fn):
            print "working: [%s]"%from_fn
            counter += 1
            #if (counter % 10)==9:
            #    time.sleep(60)
            tag_data = getPOSweb(open(from_fn, "r").read())
            if len(tag_data)>0 :
                open( to_fn , "w").write(tag_data)

'''
if __name__ == "__main__":
    main()
