#!/usr/bin/python

import sys
import random
import re

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
    #return getvalidCharList(random.randint(0,60))
    return getvalidCharList(0)

def scrambleString(s):

    sRet = ""
  
    if not s:
        return s
    strp = encodePassword(s)
    if len(strp) < 32:
        sRet += dummyString
    for iR in reversed(range(len(strp)-1)):
        sRet += strp[iR:iR+1]
    if len(sRet) < 32:
        sRet += dummyString

    app = getRandomValidCharFromList()
    k = ord(app)
    l = k + len(sRet) - 2
    sRet = app + sRet

    for i1 in range(1, len(sRet)):
        app2 = sRet[i1 : i1 + 1]
        j = findCharInList(app2)
        if j == -1:
            return sRet
        i = (j + l * (i1 + 1)) % numValidCharList
        car = getvalidCharList(i)
        sRet = substr_replace(sRet,car,i1,1)
    c = (ord(getRandomValidCharFromList())) + 2
    c2 = chr(c)
    sRet = sRet + c2
    return URLEncode(sRet)

def URLEncode(url):

    theURL = url
    #theURL =~ s/&/&amp;/g;
    url = re.sub("&","&amp",url)
    #theURL =~ s/\"\"/&quot;/g;
    url = re.sub("\"","&quot",url)
    #theURL =~ s/\'/&#039;/g;
    url = re.sub("\"","&quot",url)
    #theURL =~ s/</&lt;/g;
    url = re.sub("<","&lt",url)
    #theURL =~ s/>/&gt;/g;
    url = re.sub(">","&gt",url)
    return theURL

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
    password = sys.argv[0]
    print password
    print scrambleString(password)
