export interface DataOption {
    id: string;
    keep: boolean;
    hid: string;
    name: string;
    src: string;
    tags: Array<string>;
}

export interface DataOptions {
    hda: Array<DataOption>;
    hdca: Array<DataOption>;
}

export interface DataValue {
    values: Array<DataOption>;
}
