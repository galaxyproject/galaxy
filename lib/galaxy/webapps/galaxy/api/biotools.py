import functools
import logging
import os
import string
log = logging.getLogger(__name__)


def json_formatter(func):
    @functools.wraps(func)
    def innerfunc(cl, trans, id, **kwd):
        result = func(cl, trans, id, **kwd)
        general_dict = build_general_dict(result)
        general_dict['function'] = build_function_dict(result)
        tool_name = build_tool_name(result['tool_id'], result['tool_version'])
        general_dict["name"] = tool_name
        clean_dict(general_dict)
        return general_dict
    return innerfunc


def edam_to_uri(edam):
    """
    Build edam uri from edam data or edam format
    :param edam: edam data or format
    :return: edam uri
    """
    uri = "http://edamontology.org/{}".format(edam)
    return uri


def clean_list(jsonlist):
    """
    Recursive function in order to clean the json tool registry
    :param jsonlist: List part of a json tool registry
    :return: None
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
    Recursive function in order to clean the json tool registry
    :param jsondict: Dictionary part of a json tool registry
    :return: None
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
    Build the tool registry name regarding its long or short galaxy tool id
    :param tool_id: Galaxy tool id
    :param tool_version: Galaxy tool version
    :return: tool registry name
    :rtype: string
    """
    tbl = string.maketrans('.:/', '___')
    # with a long id galaxy, xml version is already in the id
    if tool_version in tool_id:
        return str(tool_id).translate(tbl)
    else:
        return str("_".join([tool_id, tool_version])).translate(tbl)


def format_description(description):
    """
    Ensure capital first character and final `.` in description.
    :param description: tool description
    :return: tool description for bio.tools
    :rtype: string
    """
    if not description:  # Descriptions are not mandatory in galaxy, but they are mandatory in bio.tools
        return None
    if not description.endswith('.'):
        description = "%s." % description
    return description


def get_source_registry(tool_id):
    """
    Take a tool id and return the toolshed url if the id is a long id or a empty string if id is a short id
    :param tool_id: Galaxy tool id
    :return: toolshed url for a tool or empty string
    :rtype: string
    """
    try:
        return "/".join(tool_id.replace('repos', 'view', 1).split('/')[0:-2])
    except ValueError:
        log.warning("Not well formated tool id: {}".format(tool_id))
        return ""


def build_general_dict(tool_meta_data):
    """
    Extract informations from a galaxy json tool and return the general json in the biotools format
    :param tool_meta_data: galaxy json tool
    :return: biotools dictionary
    :rtype: dictionary
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


def build_function_dict(json_tool):
    """
    Extract information from a galaxy json tool and return a list of functions in the json biotools format
    :param json_tool: galaxy json tool
    :return: list of functions in the json biotools format
    :rtype: list
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
    Extract type data param of a galaxy json tool inputs and return a list of dictionary in the json biotools format
    :param inputs_json: inputs part of a json tool
    :return: list of dictionary in the json biotools format
    :rtype: list
    """

    def inputs_extract_data(data_json):
        """
        Save param type data from a json tool galaxy in a list
        :param data_json:
        :return: None
        """
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
            listdata.append({'dataType': {'uri': 'WARNING, SEVERAL EDAM DATA', 'term': 'EDAM label placeholder'},
                             'dataFormat': list_format,
                             'dataHandle': ", ".join(data_json['extensions']),
                             'dataDescription': data_json['name']
                             })

    def inputs_extract_repeat(repeat_json):
        """
        Recursive function in order to explore repeat param of a galaxy json tool
        :param repeat_json: Repeat param part of a galaxy json tool
        :return: None
        """
        for dictinprep in repeat_json['inputs']:
            if dictinprep['type'] == "conditional":
                inputs_extract_conditional(dictinprep)
            elif dictinprep['type'] == "repeat":
                inputs_extract_repeat(dictinprep)
            elif dictinprep["type"] == "data":
                inputs_extract_data(dictinprep)

    def inputs_extract_conditional(conditional_json):
        """
        Recursive function in order to explore conditional param of a galaxy json tool
        :param conditional_json: conditional param part of a galaxy json tool
        :return: None
        """
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
    """
    Extract type output param of a galaxy json tool outputs and return a list of dictionary in the json biotools format
    :param outputs_json: output param of a galaxy json tool outputs
    :return: list of dictionary in the json biotools format
    :rtype: dictionary
    """
    listoutput = list()
    for output in outputs_json:
        outputdict = {'dataType': {'uri': edam_to_uri(output["edam_data"]), 'term': 'EDAM label placeholder'},
                      'dataFormat': [{'uri': edam_to_uri(output["edam_format"]), 'term': 'EDAM label placeholder'}],
                      'dataHandle': output['format'], 'dataDescription': output['name']
                      }
        listoutput.append(outputdict)
    return listoutput
