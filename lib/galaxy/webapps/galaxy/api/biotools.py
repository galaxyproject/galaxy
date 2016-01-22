import functools
import os
import copy
import string

def json_formater(fonc):
    @functools.wraps(fonc)
    def innerfunc(cl, trans, id, **kwd):
        result = fonc(cl, trans, id, **kwd)
        general_dict = build_general_dict(result)
        general_dict['function'] = build_fonction_dict(result)
        tool_name = build_tool_name(result['tool_id'], result['tool_version'])
        general_dict["name"] = tool_name
        clean_dict(general_dict)
        return general_dict
    return innerfunc


def edam_to_uri(edam):
    """
    :param edam:
    :return:
    """
    uri = "http://edamontology.org/{}".format(edam)
    return uri


def clean_list(jsonlist):
    """
    :param jsonlist:
    :return:
    """
    nullindexlist = []
    for elem in range(len(jsonlist)):
        if isinstance(jsonlist[elem], dict):
            clean_dict(jsonlist[elem])
        if isinstance(jsonlist[elem], list):
            clean_list(jsonlist[elem])
        if len(jsonlist[elem]) == 0:
            nullindexlist.append(elem)
    if nullindexlist:
        nullindexlist.sort(reverse=True)
        for i in nullindexlist:
            jsonlist.pop(i)
    return


def clean_dict(jsondict):
    """
    :param jsondict:
    :return:
    """
    for sonkey, sonvalue in jsondict.items():
        if sonvalue:
            if isinstance(sonvalue, dict):
                clean_dict(sonvalue)
            if isinstance(sonvalue, list):
                clean_list(sonvalue)

        if not sonvalue:
            del jsondict[sonkey]
    return


def build_tool_name(tool_id, tool_version):
    """
    @tool_id: tool_id
    builds the tool_name regarding its long id
   """
    tbl = string.maketrans('.:/', '___')
    # warning unicode is not string
    # with a long id galaxy, xml version is already in the id
    if tool_version in tool_id:
        return str(tool_id).translate(tbl)
    else:
        return str("_".join([tool_id, tool_version])).translate(tbl)


def format_description(description):
    """
    Test the first and last char of a description and replace them
    with the format adapted to Elixir
    """
    try:
        size = len(description)
        if description[size - 1] == '.':
            return description[0].upper() + description[1:size]
        else:
            return description[0].upper() + description[1:size] + '.'
    except IndexError:
        print description


def get_source_registry(tool_id):
    """
    :param tool_id:
    :return:
    """
    try:
        return "/".join(tool_id.replace('repos','view',1).split('/')[0:-2])
    except ValueError:
        print "ValueError:", tool_id
        return ""


def build_general_dict(tool_meta_data):
    """
      builds general_dict
      @param: tool_meta_data for one tool extracted from galaxy
    """

    gen_dict = {
        'version': tool_meta_data[u'tool_version'],
        'description': format_description(tool_meta_data[u'description']),
        'uses': [{
            "usesName": tool_meta_data[u'tool_id'],
            "usesHomepage": "{0}?tool_id={1}".format(os.path.join('conf.galaxy_url', "root"),
                                                     tool_meta_data[u'tool_id']),
            "usesVersion": tool_meta_data[u'tool_version']
        }],
        'collection': '',
        'sourceRegistry': get_source_registry(tool_meta_data[u'tool_id']),
        'resourceType': ["Tool"],
        'maturity': 'Stable',
        'platform': [{u'term': 'Linux'}],
        'interface': [{
            'interfaceType': "Web UI",
            'interfaceDocs': '',
            'interfaceSpecURL': '',
            'interfaceSpecFormat': ''
        }],
        'topic': [{
            'uri': "http://edamontology.org/topic_0003",
            'term': "EDAM label placeholder"
        }],
        'publications': {'publicationsPrimaryID': "None", 'publicationsOtherID': []},
        'homepage': 'conf.galaxy_url',
        'accessibility': '"Private" if conf.private else "Public"',
        'mirror': [],
        'canonicalID': '',
        'tag': [],
        'elixirInfo': {
            'elixirStatus': '',
            'elixirNode': ''
        },
        'language': [],
        'license': '',
        'cost': '',
        'docs': {
            'docsHome': '',
            'docsTermsOfUse': '',
            'docsDownload': '',
            'docsCitationInstructions': ''
        },
        'credits': {
            'creditsDeveloper': [],
            'creditsContributor': [],
            'creditsInstitution': [],
            'creditsInfrastructure': [],
            'creditsFunding': []
        },
        'contact': [{
            'contactEmail': "conf.contactEmail",
            'contactURL': '',
            'contactName': "conf.contactName",
            'contactTel': '',
            'contactRole': []
        }]
    }
    return gen_dict

def build_fonction_dict(json_tool):
    """
    :param json_tool:
    :return:
    """
    list_func = list()
    listinps = inputs_extract(json_tool['inputs'])
    listoutps = ouputs_extract(json_tool['outputs'])
    func_dict = {
        'functionDescription': json_tool['description'],
        'functionName': [{
            'uri': "http://edamontology.org/operation_0004",
            'term': 'EDAM label placeholder'
        }],
        'output': listoutps,
        'input': listinps,
        'functionHandle': " "
    }
    list_func.append(func_dict)
    return list_func

def inputs_extract(inputs_json):
    """
    :param tool_json:
    :return:
    """

    def inputs_extract_data(data_json):
        list_format = list()
        for edam_format in data_json['edam']['edam_formats']:
            list_format.append({'uri': edam_to_uri(edam_format), 'term': 'EDAM label placeholder'})

        if len(set(data_json['edam']['edam_data'])) == 1:
            listdata.append({'dataType': {'uri': edam_to_uri(data_json['edam']['edam_data'][0]),
                                          'term': 'EDAM label placeholder'},
                             'dataFormat': list_format,
                             'dataHandle': ", ".join(data_json['extensions']),
                             'dataDescription': data_json['name']
                             })
        else:
           listdata.append({'dataType': {'uri': 'WARNING, SEVERAL EDAM DATA',
                                         'term': 'EDAM label placeholder'},
                            'dataFormat': list_format,
                            'dataHandle': ", ".join(data_json['extensions']),
                            'dataDescription': data_json['name']
                            })
        #listdata.append({'type':data_json[u"type"], 'name':data_json[u"name"],'label':data_json[u"label"],
        #                 'extensions':data_json[u"extensions"],'edam':data_json[u"edam"]})

    def inputs_extract_repeat(repeat_json):
        for dictinprep in repeat_json['inputs']:
            if dictinprep['type'] == "conditional":
                inputs_extract_conditional(dictinprep)
            elif dictinprep['type'] == "repeat":
                inputs_extract_repeat(dictinprep)
            elif dictinprep["type"] == "data":
                inputs_extract_data(dictinprep)

    def inputs_extract_conditional(conditional_json):

        for case in conditional_json["cases"]:
            for dictinpcond in case["inputs"]:
                if dictinpcond['type'] == "conditional":
                    inputs_extract_conditional(dictinpcond)
                elif dictinpcond['type'] == "repeat":
                    inputs_extract_repeat(dictinpcond)
                elif dictinpcond["type"] == "data":
                    inputs_extract_data(dictinpcond)

    listdata = list()

    for dictinp in inputs_json:

        if dictinp['type'] == "conditional":
            inputs_extract_conditional(dictinp)
        elif dictinp['type'] == "repeat":
            inputs_extract_repeat(dictinp)
        elif dictinp["type"] == "data":
            inputs_extract_data(dictinp)
    return listdata


def ouputs_extract(outputs_json):
    listoutput = list()
    for output in outputs_json:
        outputdict = {'dataType': {'uri': edam_to_uri(output["edam_data"]), 'term': 'EDAM label placeholder'},
            'dataFormat': [{'uri': edam_to_uri(output["edam_format"]), 'term': 'EDAM label placeholder'}],
            'dataHandle': output['format'],
            'dataDescription': output['name']

        }
        listoutput.append(outputdict)
    return listoutput