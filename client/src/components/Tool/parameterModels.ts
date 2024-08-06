/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export type ToolParameterModel =
    | TextParameterModel
    | IntegerParameterModel
    | FloatParameterModel
    | BooleanParameterModel
    | HiddenParameterModel
    | SelectParameterModel
    | DataParameterModel
    | DataCollectionParameterModel
    | DirectoryUriParameterModel
    | RulesParameterModel
    | ColorParameterModel
    | ConditionalParameterModel
    | RepeatParameterModel
    | CwlIntegerParameterModel
    | CwlFloatParameterModel
    | CwlStringParameterModel
    | CwlBooleanParameterModel
    | CwlNullParameterModel
    | CwlFileParameterModel
    | CwlDirectoryParameterModel
    | CwlUnionParameterModel;

export interface BaseGalaxyToolParameterModelDefinition {
    name: string;
    parameter_type: string;
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
}
export interface BaseToolParameterModelDefinition {
    name: string;
    parameter_type: string;
}
export interface BooleanParameterModel {
    name: string;
    parameter_type?: "gx_boolean";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
    value?: boolean;
    truevalue?: string;
    falsevalue?: string;
}
export interface ColorParameterModel {
    name: string;
    parameter_type?: "gx_color";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
}
export interface ConditionalParameterModel {
    name: string;
    parameter_type?: "gx_conditional";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
    test_parameter: BooleanParameterModel | SelectParameterModel;
    whens: ConditionalWhen[];
}
export interface SelectParameterModel {
    name: string;
    parameter_type?: "gx_select";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
    options?: LabelValue[];
    multiple: boolean;
}
export interface LabelValue {
    label: string;
    value: string;
}
export interface ConditionalWhen {
    discriminator: boolean | string;
    parameters: ToolParameterModel[];
}
export interface TextParameterModel {
    name: string;
    parameter_type?: "gx_text";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
    area?: boolean;
    value?: string;
    default_options?: LabelValue[];
}
export interface IntegerParameterModel {
    name: string;
    parameter_type?: "gx_integer";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional: boolean;
    is_dynamic?: boolean;
    value?: number;
    min?: number;
    max?: number;
}
export interface FloatParameterModel {
    name: string;
    parameter_type?: "gx_float";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
    value?: number;
    min?: number;
    max?: number;
}
export interface HiddenParameterModel {
    name: string;
    parameter_type?: "gx_hidden";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
}
export interface DataParameterModel {
    name: string;
    parameter_type?: "gx_data";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
    extensions?: string[];
    multiple?: boolean;
    min?: number;
    max?: number;
}
export interface DataCollectionParameterModel {
    name: string;
    parameter_type?: "gx_data_collection";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
    collection_type?: string;
    extensions?: string[];
}
export interface DirectoryUriParameterModel {
    name: string;
    parameter_type: "gx_directory_uri";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
    value?: string;
}
export interface RulesParameterModel {
    name: string;
    parameter_type?: "gx_rules";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
}
export interface RepeatParameterModel {
    name: string;
    parameter_type?: "gx_repeat";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
    parameters: ToolParameterModel[];
}
export interface CwlIntegerParameterModel {
    name: string;
    parameter_type?: "cwl_integer";
}
export interface CwlFloatParameterModel {
    name: string;
    parameter_type?: "cwl_float";
}
export interface CwlStringParameterModel {
    name: string;
    parameter_type?: "cwl_string";
}
export interface CwlBooleanParameterModel {
    name: string;
    parameter_type?: "cwl_boolean";
}
export interface CwlNullParameterModel {
    name: string;
    parameter_type?: "cwl_null";
}
export interface CwlFileParameterModel {
    name: string;
    parameter_type?: "cwl_file";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
}
export interface CwlDirectoryParameterModel {
    name: string;
    parameter_type?: "cwl_directory";
    hidden?: boolean;
    label?: string;
    help?: string;
    argument?: string;
    refresh_on_change?: boolean;
    optional?: boolean;
    is_dynamic?: boolean;
}
export interface CwlUnionParameterModel {
    name: string;
    parameter_type?: "cwl_union";
    parameters: ToolParameterModel[];
}
export interface DataCollectionRequest {
    src: "hdca";
    id: string;
}
export interface DataCollectionRequestInternal {
    src: "hdca";
    id: number;
}
export interface DataRequest {
    src: "hda" | "ldda";
    id: string;
}
export interface DataRequestInteranl {
    src: "hda" | "ldda";
    id: number;
}
export interface MultiDataInstance {
    src: "hda" | "ldda" | "hdca";
    id: string;
}
export interface MultiDataInstanceInternal {
    src: "hda" | "ldda" | "hdca";
    id: number;
}
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
export interface StrictModel {}
export interface ToolParameterBundleModel {
    input_models: ToolParameterModel[];
}
