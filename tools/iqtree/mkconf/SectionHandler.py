#!/usr/bin/env python3
import sys

from xml.dom import minidom
doc = minidom.Document()
root = doc.createElement('root')

class Section:

    def __init__(self, title):
        self.title = title
        self.name  = '_'.join(title.split()[:2]).lower()
        self.arg_map = {} # flag :- param
        self.root = doc.createElement('section')

    def printSection(self, expanded=False):
        sect = self.root
        sect.setAttribute('name',  self.name  )
        sect.setAttribute('title', self.title )
        sect.setAttribute('expanded', "true" if expanded else "false")

        for flag in self.arg_map:
            param = self.makeFlag(flag)
            sect.appendChild( param )

        #print(self.title)
        #import pdb; pdb.set_trace()
        print(sect.toprettyxml())

    
        
		
    def insertFlag(self, flag, flag_params, text):
        flag = flag.strip()
        if flag not in self.arg_map:
            self.arg_map[flag] = []

        self.arg_map[flag].append(  (flag_params, text)  )

        
    def makeFlag(self,flag):
        flag_type, defaultval = self.resolveFlagType(flag)

        if flag_type == "boolean":
            return self.makeBoolean(flag, defaultval)
        if flag_type == "text":
            return self.makeText(flag, defaultval)
        if flag_type == "float":
            return self.makeNumber(flag, "float", defaultval)
        if flag_type == "integer":
            return self.makeNumber(flag, "integer", defaultval)
        if flag_type == "file":
            return self.makeFile(flag)
        if flag_type == "select":
            return self.makeSelect(flag, defaultval)
        
        print("ERROR:", flag_type, flag, self.arg_map[flag] )
        exit(-1)


    @staticmethod
    def getLabel(text):
        return text.split('. ')[0]


    def resolveFlagType(self, flag):
        array = self.arg_map[flag]

        if len(array)>1:
            return ('select',None)

        fparam, text = array[0]
        text = text.lower()
        words = text.split()

        def determineType(words, text):
            if words[0] == "specify":
                if text.find("list of")!=-1:
                    return "text"
    
                for word in words[:10]:
                    if word == "number":
                        return "integer"
                    if word == "file":
                        return "file"
                    if word == "frequency":
                        return "float"
                    if word == "prefix":
                        return "text"

                return "text"  # 'specify' defaults to text        
            

            if words[0] == "Turn" and words[1] == "on":
                return "boolean"

            # No other clues, probably bool.
            return 'boolean'


        def determineDefault(typer, words):

            for w in range(len(words)):
                word = words[w]
                if word[-6:] == "fault:":
                    next_word = words[w+1]
                    if typer == "boolean":
                        if next_word == "on":
                            return "true"
                        elif next_word == "off":
                            return "false"

                    try:
                        res = float(next_word)
                        return res
                    except ValueError:
                        pass

            return None


        type_of = determineType(words,text)
        default = determineDefault(type_of, words )

        if type_of == "integer" and default!=None:
            default = int(default)
        
        return (type_of, str(default))
                        


    def __makeSingle(self,flag):
        flag_params, text = self.arg_map[flag][0] # first and only

        param = doc.createElement('param')
        param.setAttribute('argument', flag )
        param.setAttribute('label', Section.getLabel(text) )
        param.setAttribute('help', text)
        return param

        
    def makeBoolean(self, flag, defaultval = None):
        param = self.__makeSingle(flag)
        param.setAttribute('type', 'boolean')
        param.setAttribute('value', defaultval if defaultval!=None else "false" )
        return param

    def makeText(self, flag, defaultval = None):
        param = self.__makeSingle(flag)
        param.setAttribute('type', 'text')
        if defaultval!=None:
            param.setAttribute('value',defaultval)
        return param


    def makeNumber(self, flag, typer, default=None):
        param = self.__makeSingle(flag)
        param.setAttribute('type', typer)
        if default != None:
            param.setAttribute('value', default)
        return param


    def makeFile(self,flag):
        param = self.__makeSingle(flag)
        param.setAttribute('type', 'data')
        return param
        

    def makeSelect(self,flag, defaultval = None):
        param = doc.createElement('param')
        param.setAttribute('type', 'select')
        param.setAttribute('argument', flag)

        for flag_params, text in self.arg_map[flag]:
            option = doc.createElement('option')
            option.setAttribute('value',flag_params[0])
            option.setAttribute('help', text)
            texter = doc.createTextNode(flag_params[0])

            option.appendChild(texter)
            param.appendChild(option)

        return param

