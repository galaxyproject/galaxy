import type { CollectionType } from "../History/adapters/buildCollectionModal";
import type { DataOption } from "./Elements/FormData/types";
import type { Option } from "./Elements/FormDrilldown/utilities";

export type FormParameterTypes =
    | "boolean"
    | "hidden"
    | "hidden_data"
    | "baseurl"
    | "integer"
    | "float"
    | "radio"
    | "color"
    | "directory_uri"
    | "text"
    | "password"
    | "select"
    | "data_column"
    | "genomebuild"
    | "data"
    | "data_collection"
    | "drill_down"
    | "group_tag"
    | "ftpfile"
    | "upload"
    | "rules"
    | "tags";

export type FormParameterTypeMap = {
    boolean: boolean | string;
    hidden: string;
    hidden_data: string | undefined;
    baseurl: string | undefined;
    integer: number | string;
    float: number | string;
    radio: string;
    color: string;
    directory_uri: string;
    text: string | number | string[];
    password: string | number | string[];
    select: string;
    data_column: string;
    genomebuild: string;
    data: {
        batch: boolean;
        product: boolean;
        values: DataOption[];
    };
    data_collection: {
        batch: boolean;
        product: boolean;
        values: DataOption[];
    };
    drill_down: string;
    group_tag: string;
    ftpfile: string;
    upload: string;
    rules: {
        rules: any[];
        mapping: any[];
    };
    data_dialog: string | string[];
    tags: string;
};

export type FormParameterValue = FormParameterTypeMap[FormParameterTypes];

export type FormOptionsTypeMap = {
    boolean: any;
    hidden: any;
    hidden_data: any;
    baseurl: any;
    integer: any;
    float: any;
    radio: any;
    color: any;
    directory_uri: any;
    text: any;
    password: any;
    select: any;
    data_column: any;
    genomebuild: any;
    data: {
        dce: DataOption[];
        hda: DataOption[];
        hdca: DataOption[];
        ldda: DataOption[];
    };
    data_collection: {
        dce: DataOption[];
        hda: DataOption[];
        hdca: DataOption[];
    };
    drill_down: Option[];
    group_tag: any;
    ftpfile: any;
    upload: any;
    rules: any;
    data_dialog: any;
    tags: any;
};

export type FormParameterAttributes<T extends FormParameterTypes> = {
    area?: boolean;
    argument?: string | null;
    collapsible_preview?: boolean;
    collapsible_value?: FormParameterTypeMap[T];
    color?: string;
    cls?: string;
    collection_types?: CollectionType[];
    connectable?: boolean;
    data?: {
        label: string;
        value: FormParameterTypeMap[T];
    }[];
    datalist?: {
        label: string;
        value: string;
    }[];
    default_value?: FormParameterTypeMap[T];
    display?: "checkboxes" | "radio" | "select" | "select-many";
    edam?: {
        edam_data: string[];
        edam_formats: string[];
    };
    error?: string | null;
    extensions?: string[];
    flavor?: string;
    help?: string;
    help_format?: string;
    hidden?: boolean;
    info?: string;
    is_dynamic?: boolean;
    is_workflow?: boolean;
    label?: string;
    max?: string | number;
    min?: string | number;
    model_class?:
        | "ColorToolParameter"
        | "DirectoryUriToolParameter"
        | "BaseDataToolParameter"
        | "BooleanToolParameter"
        | "DataCollectionToolParameter"
        | "DataToolParameter"
        | "FloatToolParameter"
        | "HiddenToolParameter"
        | "IntegerToolParameter"
        | "SelectToolParameter"
        | "TextToolParameter";
    multiple?: boolean | string;
    name?: string;
    optional?: boolean;
    options?: FormOptionsTypeMap[T];
    placeholder?: string;
    readonly?: boolean;
    refresh_on_change?: boolean;
    tag?: string;
    target?: Record<string, unknown>;
    textable?: boolean;
    text_value?: string;
    titleonly?: boolean;
    truevalue?: FormParameterTypeMap[T];
    type?: FormParameterTypes;
    value?: FormParameterTypeMap[T];
};
