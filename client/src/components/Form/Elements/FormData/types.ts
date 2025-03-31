type ExampleDataFile = {
    class: "File";
    filetype: string;
    location: string;
};

type ExampleDataCollection = {
    class: "Collection";
    collection_type: string;
    elements?: Array<ExampleDataFileElement | ExampleDataCollectionElement>;
};

export type ExampleDataFileElement = {
    class: "File";
    identifier: string;
    location: string;
};

export type ExampleDataCollectionElement = {
    class: "Collection";
    elements?: Array<ExampleDataFileElement | ExampleDataCollectionElement>;
    identifier: string;
    type: string;
};

export type ExampleData = ExampleDataFile | ExampleDataCollection;

export type DataOption = {
    id: string;
    hid?: number;
    is_dataset?: boolean;
    keep: boolean;
    batch: boolean;
    map_over_type?: string;
    name: string;
    src: string;
    tags: Array<string>;
};

export function isDataOption(item: object): item is DataOption {
    return !!item && "src" in item;
}

export function isExampleData(item: object): item is ExampleData {
    return !!item && "class" in item && (item as ExampleData).class !== undefined;
}
