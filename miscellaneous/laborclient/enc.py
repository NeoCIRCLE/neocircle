#!/usr/bin/python

import sys
import random
import re
from xml.sax.saxutils import escape

numValidCharList = 85
dummyString = "{{{{"


def getvalidCharList(pos):
    validcharlist = [
    "!",  "#", "$",  "%",  "&",  "(", ")",  "*",  "+",  "-",
    ".",  "0",   "1",  "2",   "3",  "4",  "5",  "6", "7", "8",
    "9", ":",  ";",  "<",  ">",  "?",  "@",  "A",  "B", "C",
    "D",  "E",  "F",  "G",  "H",  "I",  "J",  "K",  "L", "M",
    "N", "O",  "P",  "Q",  "R",  "S",  "T", "U", "V", "W",
    "X",  "Y",  "Z",  "[", "]",  "_",  "a",  "b",  "c",  "d",
    "e",  "f",  "g",  "h",  "i",  "j",  "k",  "l",  "m",  "n",
    "o",  "p",  "q",  "r",  "s",  "t",  "u",  "v",  "w",  "x",
    "y",  "z",  "{",  "|",  "}"
    ]
    return validcharlist[pos]

def encodePassword(p):

    sPass = ":"
    sTmp = ""

    if not p:
        return ""

    for i in range(len(p)):
        c = p[i:i+1]
        a = ord(c)

        sTmp = str( a + i + 1) + ":"
        sPass += sTmp
        sTmp = ""

    return sPass

def findCharInList(c):
    i = -1
    
    for j in range(numValidCharList):
        randchar = getvalidCharList(j);
        if randchar == c:
            i = j
            return i
    return i

def getRandomValidCharFromList():
    return getvalidCharList(random.randint(0,60))
    #return getvalidCharList(0)

def scrambleString(s):

    sRet = ""
  
    if not s:
        return s
    strp = encodePassword(s)
    if len(strp) < 32:
        sRet += dummyString
        #print "Added dummy "+sRet
    for iR in reversed(range(len(strp))):
        sRet += strp[iR:iR+1]
        #print "Reverse: "+sRet
    if len(sRet) < 32:
        sRet += dummyString
        #print "Added dummy2 "+sRet
    app = getRandomValidCharFromList()
    #print "Random valid char: "+app
    k = ord(app)
    l = k + len(sRet) - 2
    sRet = app + sRet
    #print "Random "+sRet+"\n"
    for i1 in range(1, len(sRet)):
        app2 = sRet[i1 : i1 + 1]
        #print "For cycle app2= "+str(app2)
        j = findCharInList(app2)
        #print "For cycle j= "+str(j)
        if j == -1:
            return sRet
        i = (j + l * (i1 + 1)) % numValidCharList
        #print "For cycle i= "+str(i)
        car = getvalidCharList(i)
        sRet = substr_replace(sRet,car,i1,1)
        #print "For cycle sRet: "+sRet+"\n"
    c = (ord(getRandomValidCharFromList())) + 2
    c2 = chr(c)
    sRet = sRet + c2
    return URLEncode(sRet)

def URLEncode(url):

    return escape(url)

def substr_replace(in_str,ch,pos,qt):
    clist = list(in_str)
    count = 0;
    tmp_str = '';
    for key in clist:
        if count != pos:
            tmp_str += key
        else:
            tmp_str += ch
        count = count+1
    return tmp_str



if __name__ == "__main__":
    password = sys.argv[1]
    print password
    #print encodePassword(password)
    print scrambleString(password)
