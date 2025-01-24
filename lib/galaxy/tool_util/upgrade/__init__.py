# Documented profile changes not covered.
# - Allow invalid values. @mvdbeek any clue what to say here. The PR is here:
# - https://github.com/galaxyproject/galaxy/pull/6264
#
# I don't want to declare these TODO but somethings could be more percise.
# - We could inspect the XML source and tell when tools are using galaxy.json and improve
#   the messaging on 17.09 for that. We can't be absolutely sure these would or would not be
#   problems but we can be more confident they might be.
# - Ditto for $HOME and the 18.01 migration.
# - We could try to walk parameters and give more specific advice on structured_like qualification.
from json import loads
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Type,
)

from typing_extensions import (
    Literal,
    NotRequired,
    TypedDict,
)

from galaxy.tool_util.parameters.case import validate_test_cases_for_tool_source
from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.tool_util.parser.xml import XmlToolSource
from galaxy.util import Element
from galaxy.util.resources import resource_string

TOOL_TOO_NEW = "Target tool has a profile that is too new, consider upgrading this script for the latest advice."
TARGET_TOO_NEW = (
    "Target upgrade version is too new for this script, consider upgrading this script for the latest advice."
)

TYPE_LEVEL = Literal["must_fix", "consider", "ready", "info"]


class AdviceCode(TypedDict):
    name: str
    level: TYPE_LEVEL
    message: str
    niche: NotRequired[bool]
    url: NotRequired[str]


upgrade_codes_json = resource_string(__name__, "upgrade_codes.json")
upgrade_codes_by_name: Dict[str, AdviceCode] = {}

for name, upgrade_object in loads(upgrade_codes_json).items():
    upgrade_object["name"] = name
    upgrade_codes_by_name[name] = cast(AdviceCode, upgrade_object)


class Advice:
    advice_code: AdviceCode
    message: Optional[str]

    def __init__(self, advice_code: AdviceCode, message: Optional[str]):
        self.advice_code = advice_code
        self.message = message

    @property
    def url(self) -> Optional[str]:
        return self.advice_code.get("url")

    @property
    def level(self) -> TYPE_LEVEL:
        return self.advice_code["level"]

    @property
    def niche(self) -> bool:
        return self.advice_code.get("niche", False)

    @property
    def advice_code_message(self) -> str:
        return self.advice_code["message"]

    def to_dict(self) -> Dict[str, Any]:
        as_dict = cast(Dict[str, Any], self.advice_code.copy())
        as_dict["advice_code_message"] = self.advice_code_message
        as_dict["message"] = self.message
        return as_dict


class AdviceCollection:
    _advice: List[Advice]

    def __init__(self):
        self._advice = []

    def add(self, code: str, message: Optional[str] = None):
        self._advice.append(Advice(upgrade_codes_by_name[code], message))

    def to_list(self) -> List[Advice]:
        return self._advice


class ProfileMigration:
    """A class offering advice on upgrading a Galaxy tool between two profile versions."""

    from_version: str
    to_version: str

    @classmethod
    def advise(cls, advice_collection: AdviceCollection, xml_file: str) -> None:
        return None


class ProfileMigration16_04(ProfileMigration):
    from_version = "16.01"
    to_version = "16.04"

    @classmethod
    def advise(cls, advice_collection: AdviceCollection, xml_file: str) -> None:
        tool_source = _xml_tool_source(xml_file)
        interpreter = tool_source.parse_interpreter()
        if interpreter:
            advice_collection.add("16_04_fix_interpreter")
        else:
            advice_collection.add("16_04_ready_interpreter")
        advice_collection.add("16_04_consider_implicit_extra_file_collection")

        if _has_matching_xpath(tool_source, ".//data[@format = 'input']"):
            advice_collection.add("16_04_fix_output_format")

        if not _has_matching_xpath(tool_source, ".//stdio") and not _has_matching_xpath(
            tool_source, ".//command[@detect_errors]"
        ):
            advice_collection.add("16_04_exit_code")


class ProfileMigration17_09(ProfileMigration):
    from_version = "16.04"
    to_version = "17.09"

    @classmethod
    def advise(cls, advice_collection: AdviceCollection, xml_file: str) -> None:
        tool_source = _xml_tool_source(xml_file)

        outputs_el = tool_source._outputs_el
        if outputs_el is not None and outputs_el.get("`provided_metadata_style`", None) is not None:
            advice_collection.add("17_09_consider_provided_metadata_style")


class ProfileMigration18_01(ProfileMigration):
    from_version = "17.09"
    to_version = "18.01"

    @classmethod
    def advise(cls, advice_collection: AdviceCollection, xml_file: str) -> None:
        tool_source = _xml_tool_source(xml_file)
        command_el = tool_source._command_el
        if command_el is not None and command_el.get("use_shared_home", None) is None:
            advice_collection.add("18_01_consider_home_directory")

        if _has_matching_xpath(tool_source, ".//outputs/collection[@structured_like]"):
            advice_collection.add("18_01_consider_structured_like")


class ProfileMigration18_09(ProfileMigration):
    from_version = "18.01"
    to_version = "18.09"

    @classmethod
    def advise(cls, advice_collection: AdviceCollection, xml_file: str) -> None:
        tool_source = _xml_tool_source(xml_file)
        tool_type = tool_source.parse_tool_type()
        if tool_type == "manage_data":
            advice_collection.add("18_09_consider_python_environment")


class ProfileMigration20_05(ProfileMigration):
    from_version = "18.09"
    to_version = "20.05"

    @classmethod
    def advise(cls, advice_collection: AdviceCollection, xml_file: str) -> None:
        tool_source = _xml_tool_source(xml_file)

        if _has_matching_xpath(tool_source, ".//configfiles/inputs"):
            advice_collection.add("20_05_consider_inputs_as_json_changes")


class ProfileMigration20_09(ProfileMigration):
    from_version = "20.05"
    to_version = "20.09"

    @classmethod
    def advise(cls, advice_collection: AdviceCollection, xml_file: str) -> None:
        tool_source = _xml_tool_source(xml_file)

        tests = tool_source.parse_tests_to_dict()
        for test in tests["tests"]:
            output_collections = test.get("output_collections")
            if not output_collections:
                continue

            for output_collection in output_collections:
                if output_collection.get("element_tests"):
                    advice_collection.add("20_09_consider_output_collection_order")

        command_el = tool_source._command_el
        if command_el is not None:
            strict = command_el.get("strict", None)
            if strict is None:
                advice_collection.add("20_09_consider_set_e")


class ProfileMigration21_09(ProfileMigration):
    from_version = "20.09"
    to_version = "21.09"

    @classmethod
    def advise(cls, advice_collection: AdviceCollection, xml_file: str) -> None:
        tool_source = _xml_tool_source(xml_file)
        for el in _find_all(tool_source, ".//data[@from_work_dir]"):
            from_work_dir = el.get("from_work_dir") or ""
            if from_work_dir != from_work_dir.strip():
                advice_collection.add("")

        tool_type = tool_source.parse_tool_type()
        if tool_type == "data_source":
            advice_collection.add("21_09_consider_python_environment")


class ProfileMigration23_0(ProfileMigration):
    from_version = "21.09"
    to_version = "23.0"

    @classmethod
    def advise(cls, advice_collection: AdviceCollection, xml_file: str) -> None:
        tool_source = _xml_tool_source(xml_file)
        for text_param in _find_all(tool_source, ".//input[@type='text']"):
            optional_tag_set = text_param.get("optional", None) is not None
            if not optional_tag_set:
                advice_collection.add("23_0_consider_optional_text")


class ProfileMigration24_0(ProfileMigration):
    from_version = "23.0"
    to_version = "24.0"

    @classmethod
    def advise(cls, advice_collection: AdviceCollection, xml_file: str) -> None:
        tool_source = _xml_tool_source(xml_file)
        tool_type = tool_source.parse_tool_type()
        if tool_type == "data_source_async":
            advice_collection.add("24_0_consider_python_environment")
        if tool_type in ["data_source_async", "data_source"]:
            advice_collection.add("24_0_request_cleaning")


class ProfileMigration24_2(ProfileMigration):
    from_version = "24.0"
    to_version = "24.2"

    @classmethod
    def advise(cls, advice_collection: AdviceCollection, xml_file: str) -> None:
        tool_source = _xml_tool_source(xml_file)
        results = validate_test_cases_for_tool_source(tool_source, use_latest_profile=True)
        for result in results:
            if result.validation_error:
                advice_collection.add("24_2_fix_test_case_validation", str(result.validation_error))


profile_migrations: List[Type[ProfileMigration]] = [
    ProfileMigration16_04,
    ProfileMigration17_09,
    ProfileMigration18_01,
    ProfileMigration18_09,
    ProfileMigration20_05,
    ProfileMigration20_09,
    ProfileMigration21_09,
    ProfileMigration23_0,
    ProfileMigration24_0,
    ProfileMigration24_2,
]

latest_supported_version = "24.2"


def advise_on_upgrade(xml_file: str, to_version: Optional[str] = None) -> List[Advice]:
    to_version = to_version or latest_supported_version
    tool_source = _xml_tool_source(xml_file)
    initial_version = tool_source.parse_profile()
    if initial_version > latest_supported_version:
        raise Exception(TOOL_TOO_NEW)
    elif to_version > latest_supported_version:
        raise Exception(TARGET_TOO_NEW)
    advice_collection = AdviceCollection()

    for migration in profile_migrations:
        if migration.to_version < initial_version:
            # tool started past here... just skip this advice
            continue
        if migration.to_version > to_version:
            # we're not advising on upgrading past this point
            break
        migration.advise(advice_collection, xml_file)

    return advice_collection.to_list()


def _xml_tool_source(xml_file: str) -> XmlToolSource:
    tool_source = get_tool_source(xml_file)
    if not isinstance(tool_source, XmlToolSource):
        raise Exception("Can only provide upgrade advice for XML tools.")
    return cast(XmlToolSource, tool_source)


def _has_matching_xpath(tool_source: XmlToolSource, xpath: str) -> bool:
    return tool_source.xml_tree.find(xpath) is not None


def _find_all(tool_source: XmlToolSource, xpath: str) -> List[Element]:
    return cast(List[Element], tool_source.xml_tree.findall(".//data[@from_work_dir]") or [])
