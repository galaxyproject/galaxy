import re
from typing import TYPE_CHECKING

from Cheetah.Parser import ParseError

from galaxy.tool_util.lint import Linter
from ._util import (
    get_code,
    is_valid_cheetah_placeholder,
)
from ..parser.util import _parse_name

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser import ToolSource


def _param_in_compiled_cheetah(param_name: str, code: str) -> bool:
    # # accession $PATH.param_name.ATTRIBUTES in cheetah gives
    # # VFFSL(SL,"PATH.param_name.ATTRIBUTES",True)
    # # for PATH and ATTRIBUTES we assume simply ([\w.]+)?
    # # since if wrong it will be discovered in a test
    # if re.search(r'VFFSL\(SL,[\"\']([\w.]+\.)?' + param_name + r'(\.[\w.]+)?[\"\'],True\)', code):
    #     return True

    # # print("checking path")
    # # accessing $PATH.param_name['ATTRIBUTE'] (ATTRIBUTE eg reverse)
    # # or $PATH.param_name['ATTRIBUTE'].FURTHER_ATTRIBUTE gives
    # # VFN(VFN(VFFSL(SL,"PATH",True),"param_name",True)['ATTRIBUTE'],"FURTHER_ATTRIBUTE",True)
    # # we simply search VFN(VFFSL(SL,"PATH",True),"param_name",True)
    # # ie ignore the ATTRIBUTES part and for PATH we assume again ([\w.]+)?
    # if re.search(r'VFN\(VFFSL\(SL,[\"\'][\w.]+[\"\'],True\),[\"\']' + param_name + r'[\"\'],True\)', code):
    #     return True

    # # all these are covered by the rawExpr regular expression below
    # # - $getVar("param_name")
    # #   gets
    # #   _v = VFFSL(SL,"getVar",False)("param_name")
    # #   if _v is not None: write(_filter(_v, rawExpr='$getVar("param_name")'))
    # # - $getVar("getvar_default", "default")
    # #   gets
    # #   _v = VFFSL(SL,"getVar",False)("getvar_default", "default")
    # #   if _v is not None: write(_filter(_v, rawExpr='$getVar("getvar_default", "default")'))
    # if re.search(r'VFFSL\(SL,[\"\']getVar[\"\'],False\)\([\"\']([\w.]+\.)?' + param_name + r'(\.[\w.]+)?[\"\'](, [^()]+)?\)', code):
    #     return True

    # # - $varExists("varexists")
    # #   gets
    # #   _v = VFFSL(SL,"varExists",False)("varexists")
    # #   if _v is not None: write(_filter(_v, rawExpr='$varExists("varexists")'))
    # # - $hasVar("hasvar")
    # #   gets
    # #   _v = VFFSL(SL,"hasVar",False)("hasvar")
    # #   if _v is not None: write(_filter(_v, rawExpr='$hasVar("hasvar")'))
    # if re.search(r'VFFSL\(SL,[\"\'](varExists|hasvar)[\"\'],False\)\([\"\']([\w.]+\.)?' + param_name + r'(\.[\w.]+)?[\'\"]\)', code):
    #     return True

    # # Also the following is possible (TODO but we could forbid it)
    # # $PATH["param_name"].ATTRIBUTES
    # # VFFSL(SL,"PATH",True)["param_name"].ATTRIBUTES
    # if re.search(r'VFFSL\(SL,[\"\'][\w.]+[\"\'],True\)\[[\"\']' + param_name + r'[\"\']\]', code):
    #     return True
    # gets
    # set $rg_id = str($rg_param('read_group_id_conditional').ID)
    # rg_id = str(VFN(VFFSL(SL,"rg_param",False)('read_group_id_conditional'),"ID",True))
    if re.search(r"(VFN|VFFSL)\(.*[\"\']([\w.]+\.)?" + param_name + r"(\.[\w.]+)?[\"\']", code):
        return True

    # #for i, r in enumerate($repeat_name)
    #     #set x = $str(r[ 'param_name' ])
    # #end for
    # the loop content gets
    # x = VFFSL(SL,"str",False)(r[ 'var_in_repeat' ])
    if re.search(r"(VFFSL|VFN)\(.*\[\s*[\"\']" + param_name + r"[\"\']\s*\]", code):
        # print(f"    G")
        return True

    # "${ ",".join( [ str( r.var_in_repeat3 ) for r in $repeat_name ] ) }"
    # gets
    # _v = ",".join( [ str( r.var_in_repeat3 ) for r in VFFSL(SL,"repeat_name",True) ] )
    # if _v is not None: write(_filter(_v, rawExpr='${ ",".join( [ str( r.var_in_repeat3 ) for r in $repeat_name ] ) }'))
    if re.search(r"rawExpr=([\"\'])(.*[^\w])?" + param_name + r"([^\w].*)?(\1)", code):
        return True

    # print("FALSE")
    return False


class InputsUsed(Linter):
    """
    check if the parameter is used somewhere, the following cases are considered:
    - in the command or a configfile
    - in an output filter
    - if it is the select of conditional
    - if there is an inputs configfile that is used
      - for data parameters data_style needs to be set for the config file
      - for other parameters the name of the config file must be used in the code

    a warning is shown if the parameter is used only in
    - template macro,
    - output action, or
    - label of an output

    otherwise
    - if the parameter only appears in change_format
    - or if none of the previous cases apply
    """

    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        tool_xml = getattr(tool_source, "xml_tree", None)
        if not tool_xml:
            return

        try:
            code, template_code, filter_code, label_code, action_code = get_code(tool_xml)
        except ParseError as pe:
            lint_ctx.error(f"Invalid cheetah found{pe}", linter=cls.name(), node=tool_xml.getroot())
            return

        inputs = tool_xml.findall("./inputs//param")
        for param in inputs:
            try:
                param_name = _parse_name(param.attrib.get("name"), param.attrib.get("argument"))
            except ValueError:
                continue
            if not is_valid_cheetah_placeholder(param_name):
                continue
            if _param_in_compiled_cheetah(param, param_name, code):
                continue
            if param_name in filter_code:
                continue
            # TODO We need to check if the referenced parameter is the current one
            if (
                tool_xml.find("./inputs//param/options[@from_dataset]") is not None
                or tool_xml.find("./inputs//param/options/filter[@ref]") is not None
            ):
                continue
            if param.getparent().tag == "conditional":
                continue

            conf_inputs = tool_xml.find("./configfiles/inputs")
            if conf_inputs is not None:  # in this it's really hard to know
                param_type = param.attrib.get("type")
                if param_type in ["data", "collection"]:
                    if not conf_inputs.attrib.get("data_style"):
                        lint_ctx.error(
                            f"Param input [{param_name}] not found in command or configfiles. Does the present inputs config miss the 'data_style' attribute?",
                            linter=cls.name(),
                            node=param,
                        )
                inputs_conf_name = conf_inputs.attrib.get("name", conf_inputs.attrib.get("filename", None))
                if inputs_conf_name:
                    if not re.search(r"(^|[^\w])" + inputs_conf_name + r"([^\w]|$)", code):
                        lint_ctx.error(
                            f"Param input [{param_name}] only used inputs configfile {inputs_conf_name}, but this is not used in the command",
                            linter=cls.name(),
                            node=param,
                        )
                continue

            change_format = tool_xml.find(f"./outputs//change_format/when[@input='{param_name}']") is not None
            template = re.search(r"(^|[^\w])" + param_name + r"([^\w]|$)", template_code) is not None
            action = re.search(r"(^|[^\w])" + param_name + r"([^\w]|$)", action_code) is not None
            label = re.search(r"[^\w]" + param_name + r"([^\w]|$)", label_code) is not None
            if template or action or label:
                if template + action + label == 1:
                    only = "only "
                else:
                    only = ""
                # TODO check that template is used??
                if template:
                    lint_ctx.warn(
                        f"Param input [{param_name}] {only}used in a template macro, use a macro token instead.",
                        linter=cls.name(),
                        node=param,
                    )
                if action:
                    lint_ctx.warn(
                        f"Param input [{param_name}] {only}found in output actions, better use extended metadata.",
                        linter=cls.name(),
                        node=param,
                    )
                if label:
                    lint_ctx.warn(
                        f"Param input [{param_name}] {only}found in a label attribute, this is discouraged.",
                        linter=cls.name(),
                        node=param,
                    )
                continue

            if change_format:
                lint_ctx.error(
                    f"Param input [{param_name}] is only used in a change_format tag", linter=cls.name(), node=param
                )
            else:
                lint_ctx.error(
                    f"Param input [{param_name}] not found in command or configfiles.", linter=cls.name(), node=param
                )
