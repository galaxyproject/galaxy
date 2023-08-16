export interface DataOption {
    id: string;
    keep: boolean;
    hid: string;
    name: string;
    src: string;
    tags: Array<string>;
}

export interface DataValue {
    values: Array<DataOption>;
}
