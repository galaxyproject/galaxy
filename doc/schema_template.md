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

$tag:tool://element[@name='tool']
$tag:tool|description://element[@name='tool']//element[@name='description']
$tag:tool|version_command://complexType[@name='VersionCommand']
$tag:tool|command://element[@name='tool']//element[@name='command'] hide_attributes
$tag:tool|inputs://complexType[@name='Inputs']
$tag:tool|inputs|section://complexType[@name='Section']
$tag:tool|inputs|repeat://complexType[@name='Repeat']
$tag:tool|inputs|conditional://complexType[@name='Conditional']
$tag:tool|inputs|conditional|when://complexType[@name='ConditionalWhen']
$tag:tool|inputs|param://complexType[@name='Param']
$tag:tool|inputs|param|validator://complexType[@name='Validator']
$tag:tool|inputs|param|option://complexType[@name='ParamOption']
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
$tag:tool|configfiles://complexType[@name='ConfigFiles']
$tag:tool|configfiles|configfile://complexType[@name='ConfigFile']
$tag:tool|configfiles|inputs://complexType[@name='ConfigInputs']
$tag:tool|environment_variables://complexType[@name='EnvironmentVariables']
$tag:tool|environment_variables|environment_variable://complexType[@name='EnvironmentVariable']
$tag:tool|outputs://complexType[@name='Outputs']
$tag:tool|outputs|data://complexType[@name='Data']
$tag:tool|outputs|data|filter://complexType[@name='OutputFilter']
$tag:tool|outputs|data|change_format://complexType[@name='ChangeFormat']
$tag:tool|outputs|data|change_format|when://complexType[@name='ChangeFormatWhen']
$tag:tool|outputs|data|actions://complexType[@name='Actions']
$tag:tool|outputs|data|actions|conditional://complexType[@name='ActionsConditional']
$tag:tool|outputs|data|actions|conditional|when://complexType[@name='ActionsConditionalWhen']
$tag:tool|outputs|data|actions|action://complexType[@name='Action']
$tag:tool|outputs|data|discover_datasets://complexType[@name='OutputDiscoverDatasets']
$tag:tool|outputs|collection://complexType[@name='Collection']
$tag:tool|outputs|collection|filter://complexType[@name='OutputFilter']
$tag:tool|outputs|collection|discover_datasets://complexType[@name='OutputCollectionDiscoverDatasets']
$tag:tool|tests://complexType[@name='Tests']
$tag:tool|tests|test://complexType[@name='Test']
$tag:tool|tests|test|param://complexType[@name='TestParam']
$tag:tool|tests|test|repeat://complexType[@name='TestRepeat']
$tag:tool|tests|test|section://complexType[@name='TestSection']
$tag:tool|tests|test|conditional://complexType[@name='TestConditional']
$tag:tool|tests|test|output://complexType[@name='TestOutput']
$tag:tool|tests|test|output|discover_dataset://complexType[@name='TestDiscoveredDataset']
$tag:tool|tests|test|output|metadata://complexType[@name='TestOutputMetadata']
$tag:tool|tests|test|output|assert_contents://group[@name='TestOutputElement']//element[@name='assert_contents']
$tag:tool|tests|test|output_collection://complexType[@name='TestOutputCollection']
$tag:tool|tests|test|assert_command://group[@name='TestParamElement']//element[@name='assert_command']
$tag:tool|tests|test|assert_stdout://group[@name='TestParamElement']//element[@name='assert_stdout']
$tag:tool|tests|test|assert_stderr://group[@name='TestParamElement']//element[@name='assert_stderr']
$tag:tool|code://complexType[@name='Code']
$tag:tool|requirements://complexType[@name='Requirements']
$tag:tool|requirements|requirement://complexType[@name='Requirement']
$tag:tool|requirements|container://complexType[@name='Container']
$tag:tool|stdio://complexType[@name='Stdio']
$tag:tool|stdio|exit_code://complexType[@name='ExitCode'] hide_attributes
$tag:tool|stdio|regex://complexType[@name='Regex'] hide_attributes
$tag:tool|help://element[@name='tool']//element[@name='help']
$tag:tool|citations://complexType[@name='Citations']
$tag:tool|citations|citation://complexType[@name='Citation']
