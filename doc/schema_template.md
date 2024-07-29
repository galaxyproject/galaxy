# Galaxy Tool XML File

The XML File for a Galaxy tool, generally referred to as the "tool config
file" or "wrapper", serves a number of purposes. First, it lays out the user
interface for the tool (e.g. form fields, text, help, etc.). Second, it
provides the glue that links your tool to Galaxy by telling Galaxy how to
invoke it, what options to pass, and what files it will produce as output.

If you find a bug please report it [here](https://github.com/galaxyproject/galaxy/issues/new).

This document serves as reference documentation. If you would like to learn
how to build tools for Galaxy,
[Planemo](https://planemo.readthedocs.io/en/latest/writing.html) features a
number of tutorials on building Galaxy tools that would better serve that purpose.

```{contents} Contents
:depth: 1
:local:
```

$tag:tool://element[@name='tool']
$tag:tool|description://element[@name='tool']//element[@name='description']
$tag:tool|macros://complexType[@name='Macros']
$tag:tool|edam_topics://complexType[@name='EdamTopics']
$tag:tool|edam_operations://complexType[@name='EdamOperations']
$tag:tool|xrefs://complexType[@name='xrefs']
$tag:tool|xrefs|xref://complexType[@name='xref']
$tag:tool|creator://complexType[@name='Creator']
$tag:tool|creator|person://complexType[@name='Person']
$tag:tool|creator|organization://complexType[@name='Organization']
$tag:tool|requirements://complexType[@name='Requirements']
$tag:tool|requirements|requirement://complexType[@name='Requirement']
$tag:tool|requirements|container://complexType[@name='Container']
$tag:tool|required_files://complexType[@name='RequiredFiles']
$tag:tool|required_files|include://complexType[@name='RequiredFileInclude']
$tag:tool|required_files|exclude://complexType[@name='RequiredFileExclude']
$tag:tool|code://complexType[@name='Code']
$tag:tool|stdio://complexType[@name='Stdio']
$tag:tool|stdio|exit_code://complexType[@name='ExitCode'] hide_attributes
$tag:tool|stdio|regex://complexType[@name='Regex'] hide_attributes
$tag:tool|version_command://complexType[@name='VersionCommand']
$tag:tool|command://complexType[@name='Command']
$tag:tool|environment_variables://complexType[@name='EnvironmentVariables']
$tag:tool|environment_variables|environment_variable://complexType[@name='EnvironmentVariable']
$tag:tool|configfiles://complexType[@name='ConfigFiles']
$tag:tool|configfiles|configfile://complexType[@name='ConfigFile']
$tag:tool|configfiles|inputs://complexType[@name='ConfigInputs']
$tag:tool|inputs://complexType[@name='Inputs']
$tag:tool|inputs|section://complexType[@name='Section']
$tag:tool|inputs|repeat://complexType[@name='Repeat']
$tag:tool|inputs|conditional://complexType[@name='Conditional']
$tag:tool|inputs|conditional|when://complexType[@name='ConditionalWhen']
$tag:tool|inputs|param://complexType[@name='Param']
$tag:tool|inputs|param|validator://complexType[@name='Validator']
$tag:tool|inputs|param|option://complexType[@name='ParamSelectOption']
$tag:tool|inputs|param|conversion://complexType[@name='ParamConversion']
$tag:tool|inputs|param|options://complexType[@name='ParamOptions']
$tag:tool|inputs|param|options|column://complexType[@name='Column']
$tag:tool|inputs|param|options|filter://complexType[@name='Filter']
$tag:tool|inputs|param|sanitizer://complexType[@name='Sanitizer']
$tag:tool|inputs|param|sanitizer|valid://complexType[@name='SanitizerValid']
$tag:tool|inputs|param|sanitizer|valid|add://complexType[@name='SanitizerValidAdd']
$tag:tool|inputs|param|sanitizer|valid|remove://complexType[@name='SanitizerValidRemove']
$tag:tool|inputs|param|sanitizer|mapping://complexType[@name='SanitizerMapping']
$tag:tool|inputs|param|sanitizer|mapping|add://complexType[@name='SanitizerMappingAdd']
$tag:tool|inputs|param|sanitizer|mapping|remove://complexType[@name='SanitizerMappingRemove']
$tag:tool|request_param_translation://complexType[@name='RequestParameterTranslation']
$tag:tool|request_param_translation|request_param://complexType[@name='RequestParameter']
$tag:tool|request_param_translation|request_param|append_param://complexType[@name='RequestParameterAppend']
$tag:tool|request_param_translation|request_param|append_param|value://complexType[@name='RequestParameterAppendValue']
$tag:tool|request_param_translation|request_param|value_translation://complexType[@name='RequestParameterValueTranslation']
$tag:tool|request_param_translation|request_param|value_translation|value://complexType[@name='RequestParameterValueTranslationValue']
$tag:tool|outputs://complexType[@name='Outputs']
$tag:tool|outputs|data://complexType[@name='OutputData']
$tag:tool|outputs|data|filter://complexType[@name='OutputFilter']
$tag:tool|outputs|data|change_format://complexType[@name='ChangeFormat']
$tag:tool|outputs|data|change_format|when://complexType[@name='ChangeFormatWhen']
$tag:tool|outputs|data|actions://complexType[@name='Actions']
$tag:tool|outputs|data|actions|conditional://complexType[@name='ActionsConditional']
$tag:tool|outputs|data|actions|conditional|when://complexType[@name='ActionsConditionalWhen']
$tag:tool|outputs|data|actions|action://complexType[@name='Action']
$tag:tool|outputs|data|actions|action|option://complexType[@name='ActionsOption']
$tag:tool|outputs|data|discover_datasets://complexType[@name='OutputDiscoverDatasets']
$tag:tool|outputs|collection://complexType[@name='OutputCollection']
$tag:tool|outputs|collection|data://complexType[@name='OutputCollectionData']
$tag:tool|outputs|collection|filter://complexType[@name='OutputFilter']
$tag:tool|outputs|collection|discover_datasets://complexType[@name='OutputCollectionDiscoverDatasets']
$tag:tool|tests://complexType[@name='Tests']
$tag:tool|tests|test://complexType[@name='Test']
$tag:tool|tests|test|param://complexType[@name='TestParam']
$tag:tool|tests|test|param|metadata://complexType[@name='TestParamMetadata']
$tag:tool|tests|test|param|collection://complexType[@name='TestCollection']
$tag:tool|tests|test|repeat://complexType[@name='TestRepeat']
$tag:tool|tests|test|section://complexType[@name='TestSection']
$tag:tool|tests|test|conditional://complexType[@name='TestConditional']
$tag:tool|tests|test|output://complexType[@name='TestOutput']
$tag:tool|tests|test|output|discovered_dataset://complexType[@name='TestDiscoveredDataset']
$tag:tool|tests|test|output|metadata://complexType[@name='TestOutputMetadata']
$tag:tool|tests|test|output|assert_contents://group[@name='TestOutputElement']//element[@name='assert_contents']
$tag:tool|tests|test|output_collection://complexType[@name='TestOutputCollection']
$tag:tool|tests|test|assert_command://group[@name='TestParamElement']//element[@name='assert_command']
$tag:tool|tests|test|assert_stdout://group[@name='TestParamElement']//element[@name='assert_stdout']
$tag:tool|tests|test|assert_stderr://group[@name='TestParamElement']//element[@name='assert_stderr']
$tag:tool|help://element[@name='tool']//element[@name='help']
$tag:tool|citations://complexType[@name='Citations']
$tag:tool|citations|citation://complexType[@name='Citation']
