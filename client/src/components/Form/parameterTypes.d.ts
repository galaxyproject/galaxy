import type { CollectionType } from "@/components/History/adapters/buildCollectionModal";

// TODO: stricter types
export type FormParameterValue = string | number | boolean | undefined | FormParameterClass | FormParameterDataField;
export type FormParameterAttributes = {
    value?: FormParameterValue;
    collapsible_value?: FormParameterValue;
    default_value?: FormParameterValue;
    placeholder?: string;
    hidden?: boolean;
    collapsible_preview?: boolean;
    text_value?: string;
    argument?: string;
    label?: string;
    name?: string;
    titleonly?: boolean;
    optional?: boolean;
    extensions?: string[];
    info?: string;
    min?: string | number;
    max?: string | number;
    is_workflow?: boolean;
    readonly?: boolean;
    area?: boolean;
    multiple?: boolean;
    datalist?: { value: string; label?: string }[];
    color?: string;
    cls?: string;
    options?: Option[] | Record<string, DataOption[]>;
    data?: Option[];
    display?: string;
    target?: Record<string, any>;
    collection_types?: CollectionType[];
    tag?: string;
    connectable?: boolean;
    flavor?: string;
};

export type FormParameterClassName = "ConnectedValue" | "RuntimeValue";
export type FormParameterClass = { __class__: FormParameterClassName };

export type FormParameterDataField = {
    src: string;
};

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
