/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export interface AdaptedDataCollectionPromoteCollectionElementToCollectionRequestInternal {
    src: "CollectionAdapter";
    adapter_type: "PromoteCollectionElementToCollection";
    adapting: DatasetCollectionElementReference;
}
export interface DatasetCollectionElementReference {
    src: "dce";
    id: number;
}
export interface AdaptedDataCollectionPromoteDatasetToCollectionRequest {
    src: "CollectionAdapter";
    adapter_type: "PromoteDatasetToCollection";
    collection_type: "list" | "paired_or_unpaired";
    adapting: DataRequestHda;
}
export interface DataRequestHda {
    src?: "hda";
    id: string;
}
export interface AdaptedDataCollectionPromoteDatasetToCollectionRequestInternal {
    src: "CollectionAdapter";
    adapter_type: "PromoteDatasetToCollection";
    collection_type: "list" | "paired_or_unpaired";
    adapting: DataRequestInternalHda;
}
export interface DataRequestInternalHda {
    src: "hda";
    id: number;
}
export interface AdaptedDataCollectionPromoteDatasetsToCollectionRequest {
    src: "CollectionAdapter";
    adapter_type: "PromoteDatasetsToCollection";
    collection_type: "paired" | "paired_or_unpaired";
    adapting: AdapterElementRequest[];
}
export interface AdapterElementRequest {
    src?: "hda";
    id: string;
    name: string;
}
export interface AdaptedDataCollectionPromoteDatasetsToCollectionRequestInternal {
    src: "CollectionAdapter";
    adapter_type: "PromoteDatasetsToCollection";
    collection_type: "paired" | "paired_or_unpaired";
    adapting: AdapterElementRequestInternal[];
}
export interface AdapterElementRequestInternal {
    src: "hda";
    id: number;
    name: string;
}
export interface AdaptedDataCollectionRequestBase {
    src: "CollectionAdapter";
}
export interface BaseDataRequest {
    location: string;
    name?: string | null;
    ext: string;
    dbkey?: string;
    deferred?: boolean;
    created_from_basename?: string | null;
    info?: string | null;
    tags?: string[] | null;
    hashes?: DatasetHash[] | null;
    space_to_tab?: boolean;
    to_posix_lines?: boolean;
}
export interface DatasetHash {
    hash_function: "MD5" | "SHA-1" | "SHA-256" | "SHA-512";
    hash_value: string;
}
export interface BaseGalaxyToolParameterModelDefinition {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type: string;
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
}
export interface BaseToolParameterModelDefinition {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type: string;
}
export interface BaseUrlParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_baseurl";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "baseurl";
}
export interface BatchDataInstance {
    src: "hda" | "ldda" | "hdca";
    id: string;
}
export interface BatchDataInstanceInternal {
    src: "hda" | "ldda" | "hdca";
    id: number;
}
export interface BooleanParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_boolean";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "boolean";
    value?: boolean | null;
    truevalue?: string | null;
    falsevalue?: string | null;
}
export interface CollectionElementCollectionRequestUri {
    class: "Collection";
    /**
     * A unique identifier for this element within the collection.
     */
    identifier: string;
    collection_type: string;
    elements: (CollectionElementCollectionRequestUri | CollectionElementDataRequestUri)[];
}
export interface CollectionElementDataRequestUri {
    location: string;
    name?: string | null;
    ext: string;
    dbkey?: string;
    deferred?: boolean;
    created_from_basename?: string | null;
    info?: string | null;
    tags?: string[] | null;
    hashes?: DatasetHash[] | null;
    space_to_tab?: boolean;
    to_posix_lines?: boolean;
    class: "File";
    /**
     * A unique identifier for this element within the collection.
     */
    identifier: string;
}
export interface ColorParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_color";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "color";
    value?: string | null;
}
export interface ConditionalParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_conditional";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "conditional";
    test_parameter: BooleanParameterModel | SelectParameterModel;
    whens: ConditionalWhen[];
}
export interface SelectParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_select";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "select";
    options?: LabelValue[] | null;
    multiple?: boolean;
    validators?: NoOptionsParameterValidatorModel[];
}
export interface LabelValue {
    label: string;
    value: string;
    selected: boolean;
}
export interface NoOptionsParameterValidatorModel {
    type?: "no_options";
    message?: string | null;
    implicit?: boolean;
    negate?: boolean;
}
export interface ConditionalWhen {
    discriminator: boolean | string;
    parameters: (
        | CwlIntegerParameterModel
        | CwlFloatParameterModel
        | CwlStringParameterModel
        | CwlBooleanParameterModel
        | CwlNullParameterModel
        | CwlFileParameterModel
        | CwlDirectoryParameterModel
        | CwlUnionParameterModel
        | TextParameterModel
        | IntegerParameterModel
        | FloatParameterModel
        | BooleanParameterModel
        | HiddenParameterModel
        | SelectParameterModel
        | DataParameterModel
        | DataCollectionParameterModel
        | DataColumnParameterModel
        | DirectoryUriParameterModel
        | RulesParameterModel
        | DrillDownParameterModel
        | GroupTagParameterModel
        | BaseUrlParameterModel
        | GenomeBuildParameterModel
        | ColorParameterModel
        | ConditionalParameterModel
        | RepeatParameterModel
        | SectionParameterModel
    )[];
    is_default_when: boolean;
}
export interface CwlIntegerParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "cwl_integer";
}
export interface CwlFloatParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "cwl_float";
}
export interface CwlStringParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "cwl_string";
}
export interface CwlBooleanParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "cwl_boolean";
}
export interface CwlNullParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "cwl_null";
}
export interface CwlFileParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "cwl_file";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
}
export interface CwlDirectoryParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "cwl_directory";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
}
export interface CwlUnionParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "cwl_union";
    parameters: (
        | CwlIntegerParameterModel
        | CwlFloatParameterModel
        | CwlStringParameterModel
        | CwlBooleanParameterModel
        | CwlNullParameterModel
        | CwlFileParameterModel
        | CwlDirectoryParameterModel
        | CwlUnionParameterModel
    )[];
}
export interface TextParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_text";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "text";
    area?: boolean;
    value?: string | null;
    default_options?: LabelValue[];
    validators?: (
        | LengthParameterValidatorModel
        | RegexParameterValidatorModel
        | ExpressionParameterValidatorModel
        | EmptyFieldParameterValidatorModel
    )[];
}
export interface LengthParameterValidatorModel {
    type?: "length";
    message?: string | null;
    implicit?: boolean;
    min?: number | null;
    max?: number | null;
    negate?: boolean;
}
/**
 * Check if a regular expression **matches** the value, i.e. appears
 * at the beginning of the value. To enforce a match of the complete value use
 * ``$`` at the end of the expression. The expression is given is the content
 * of the validator tag. Note that for ``selects`` each option is checked
 * separately.
 */
export interface RegexParameterValidatorModel {
    type?: "regex";
    message?: string | null;
    implicit?: boolean;
    negate?: boolean;
    expression: string;
}
/**
 * Check if a one line python expression given expression evaluates to True.
 *
 * The expression is given is the content of the validator tag.
 */
export interface ExpressionParameterValidatorModel {
    type?: "expression";
    message?: string | null;
    implicit?: boolean;
    negate?: boolean;
    expression: string;
}
export interface EmptyFieldParameterValidatorModel {
    type?: "empty_field";
    message?: string | null;
    implicit?: boolean;
    negate?: boolean;
}
export interface IntegerParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_integer";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    optional?: boolean;
    type: "integer";
    value?: number | null;
    min?: number | null;
    max?: number | null;
    validators?: InRangeParameterValidatorModel[];
}
export interface InRangeParameterValidatorModel {
    type?: "in_range";
    message?: string | null;
    implicit?: boolean;
    min?: number | null;
    max?: number | null;
    exclude_min?: boolean;
    exclude_max?: boolean;
    negate?: boolean;
}
export interface FloatParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_float";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "float";
    value?: number | null;
    min?: number | null;
    max?: number | null;
    validators?: InRangeParameterValidatorModel[];
}
export interface HiddenParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_hidden";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "hidden";
    value: string | null;
    validators?: (
        | LengthParameterValidatorModel
        | RegexParameterValidatorModel
        | ExpressionParameterValidatorModel
        | EmptyFieldParameterValidatorModel
    )[];
}
export interface DataParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_data";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "data";
    /**
     * Limit inputs to datasets with these extensions. Use 'data' to allow all input datasets.
     */
    extensions?: string[];
    /**
     * Allow multiple values to be selected.
     */
    multiple?: boolean;
    min?: number | null;
    max?: number | null;
}
export interface DataCollectionParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_data_collection";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "data_collection";
    collection_type?: string | null;
    extensions?: string[];
    value: {
        [k: string]: unknown;
    } | null;
}
export interface DataColumnParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_data_column";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "data_column";
    multiple: boolean;
    value?: number | number[] | null;
}
export interface DirectoryUriParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_directory_uri";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "directory";
    validators?: (
        | LengthParameterValidatorModel
        | RegexParameterValidatorModel
        | ExpressionParameterValidatorModel
        | EmptyFieldParameterValidatorModel
    )[];
}
export interface RulesParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_rules";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "rules";
}
export interface DrillDownParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_drill_down";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "drill_down";
    options?: DrillDownOptionsDict[] | null;
    multiple: boolean;
    hierarchy: "recurse" | "exact";
}
export interface DrillDownOptionsDict {
    name: string | null;
    value: string;
    options: DrillDownOptionsDict[];
    selected: boolean;
    [k: string]: unknown;
}
export interface GroupTagParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_group_tag";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "group_tag";
    multiple: boolean;
}
export interface GenomeBuildParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_genomebuild";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "genomebuild";
    multiple: boolean;
}
export interface RepeatParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_repeat";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "repeat";
    parameters: (
        | CwlIntegerParameterModel
        | CwlFloatParameterModel
        | CwlStringParameterModel
        | CwlBooleanParameterModel
        | CwlNullParameterModel
        | CwlFileParameterModel
        | CwlDirectoryParameterModel
        | CwlUnionParameterModel
        | TextParameterModel
        | IntegerParameterModel
        | FloatParameterModel
        | BooleanParameterModel
        | HiddenParameterModel
        | SelectParameterModel
        | DataParameterModel
        | DataCollectionParameterModel
        | DataColumnParameterModel
        | DirectoryUriParameterModel
        | RulesParameterModel
        | DrillDownParameterModel
        | GroupTagParameterModel
        | BaseUrlParameterModel
        | GenomeBuildParameterModel
        | ColorParameterModel
        | ConditionalParameterModel
        | RepeatParameterModel
        | SectionParameterModel
    )[];
    min?: number | null;
    max?: number | null;
}
export interface SectionParameterModel {
    /**
     * Parameter name. Used when referencing parameter in workflows or inside command templating.
     */
    name: string;
    parameter_type?: "gx_section";
    hidden?: boolean;
    /**
     * Will be displayed on the tool page as the label of the parameter.
     */
    label?: string | null;
    /**
     * Short bit of text, rendered on the tool form just below the associated field to provide information about the field.
     */
    help?: string | null;
    /**
     * If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit).
     */
    argument?: string | null;
    is_dynamic?: boolean;
    /**
     * If `false`, parameter must have a value.
     */
    optional?: boolean;
    type: "section";
    parameters: (
        | CwlIntegerParameterModel
        | CwlFloatParameterModel
        | CwlStringParameterModel
        | CwlBooleanParameterModel
        | CwlNullParameterModel
        | CwlFileParameterModel
        | CwlDirectoryParameterModel
        | CwlUnionParameterModel
        | TextParameterModel
        | IntegerParameterModel
        | FloatParameterModel
        | BooleanParameterModel
        | HiddenParameterModel
        | SelectParameterModel
        | DataParameterModel
        | DataCollectionParameterModel
        | DataColumnParameterModel
        | DirectoryUriParameterModel
        | RulesParameterModel
        | DrillDownParameterModel
        | GroupTagParameterModel
        | BaseUrlParameterModel
        | GenomeBuildParameterModel
        | ColorParameterModel
        | ConditionalParameterModel
        | RepeatParameterModel
        | SectionParameterModel
    )[];
}
export interface ConnectedValue {
    __class__: "ConnectedValue";
}
export interface DataCollectionPaired {
    forward: DataInternalJson;
    reverse: DataInternalJson;
}
export interface DataInternalJson {
    class: "File";
    /**
     * The base name of the file, that is, the name of the file without any leading directory path
     */
    basename: string;
    location: string;
    /**
     * The absolute path to the file on disk.
     */
    path: string;
    listing: string[] | null;
    /**
     * The basename root such that nameroot + nameext == basename
     */
    nameroot: string | null;
    /**
     * The basename extension such that nameroot + nameext == basename
     */
    nameext: string | null;
    /**
     * The datatype extension of the file, e.g. 'txt', 'bam', 'fastq.gz'.
     */
    format: string;
    checksum: string | null;
    size: number;
}
export interface DataCollectionRequest {
    src: "hdca";
    id: string;
}
export interface DataCollectionRequestInternal {
    src: "hdca";
    id: number;
}
export interface DataRequestCollectionUri {
    class: "Collection";
    collection_type: string;
    elements: (CollectionElementCollectionRequestUri | CollectionElementDataRequestUri)[];
    deferred?: boolean;
    name?: string | null;
}
export interface DataRequestHdca {
    src?: "hdca";
    id: string;
}
export interface DataRequestInternalHdca {
    src: "hdca";
    id: number;
}
export interface DataRequestInternalLdda {
    src: "ldda";
    id: number;
}
export interface DataRequestLd {
    /**
     * @deprecated
     */
    src: "ld";
    id: string;
}
export interface DataRequestLdda {
    src?: "ldda";
    id: string;
}
export interface DataRequestUri {
    location: string;
    name?: string | null;
    ext: string;
    dbkey?: string;
    deferred?: boolean;
    created_from_basename?: string | null;
    info?: string | null;
    tags?: string[] | null;
    hashes?: DatasetHash[] | null;
    space_to_tab?: boolean;
    to_posix_lines?: boolean;
    src?: "url";
}
export interface FileRequestUri {
    location: string;
    name?: string | null;
    ext: string;
    dbkey?: string;
    deferred?: boolean;
    created_from_basename?: string | null;
    info?: string | null;
    tags?: string[] | null;
    hashes?: DatasetHash[] | null;
    space_to_tab?: boolean;
    to_posix_lines?: boolean;
    class: "File";
}
export interface LegacyRequestModelAttributes {}
export interface RulesMapping {
    type: string;
    columns: number[];
}
export interface RulesModel {
    rules: {
        [k: string]: unknown;
    }[];
    mappings: RulesMapping[];
}
export interface StaticValidatorModel {
    type:
        | "expression"
        | "regex"
        | "in_range"
        | "length"
        | "metadata"
        | "dataset_metadata_equal"
        | "unspecified_build"
        | "no_options"
        | "empty_field"
        | "empty_dataset"
        | "empty_extra_files_path"
        | "dataset_metadata_in_data_table"
        | "dataset_metadata_not_in_data_table"
        | "dataset_metadata_in_range"
        | "value_in_data_table"
        | "value_not_in_data_table"
        | "dataset_ok_validator"
        | "dataset_metadata_in_file";
    message?: string | null;
    implicit?: boolean;
}
export interface StrictModel {}
export interface ToolParameterBundleModel {
    parameters: (
        | CwlIntegerParameterModel
        | CwlFloatParameterModel
        | CwlStringParameterModel
        | CwlBooleanParameterModel
        | CwlNullParameterModel
        | CwlFileParameterModel
        | CwlDirectoryParameterModel
        | CwlUnionParameterModel
        | TextParameterModel
        | IntegerParameterModel
        | FloatParameterModel
        | BooleanParameterModel
        | HiddenParameterModel
        | SelectParameterModel
        | DataParameterModel
        | DataCollectionParameterModel
        | DataColumnParameterModel
        | DirectoryUriParameterModel
        | RulesParameterModel
        | DrillDownParameterModel
        | GroupTagParameterModel
        | BaseUrlParameterModel
        | GenomeBuildParameterModel
        | ColorParameterModel
        | ConditionalParameterModel
        | RepeatParameterModel
        | SectionParameterModel
    )[];
}
export interface ToolSourceBaseModel {}
