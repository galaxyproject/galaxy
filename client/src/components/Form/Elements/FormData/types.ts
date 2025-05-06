/**
 * The Uri types here are based on `DataOrCollectionRequest` defined in
 * `lib/galaxy/tool_util_models/parameters.py`.
 */

type BaseDataUri = {
    // Must have one of these 2
    url?: string;
    location?: string; // alias for `url`

    extension?: string;
    filetype?: string; // alias for `ext`)
    ext?: string;

    name?: string;
};

type DataUriData = BaseDataUri & {
    src: "url";
};

type DataUriFile = BaseDataUri & {
    // Must have one of these 2
    class?: "File";
    class_?: "File"; // alias for `class`
};

export type DataUriCollectionElementFile = DataUriFile & {
    identifier: string;
};

export type DataUriCollectionElementCollection = {
    // Must have one of these 2
    class?: "Collection";
    class_?: "Collection"; // alias for `class`

    identifier: string;

    type?: string;
    collection_type?: string;

    elements: DataUriCollectionElement[];
};

type DataUriCollection = {
    // Must have one of these 2
    class?: "Collection";
    class_?: "Collection"; // alias for `class`

    collection_type: string;
    elements: DataUriCollectionElement[];
    deferred?: boolean;
    name?: string;
};

export type DataUriCollectionElement = DataUriCollectionElementFile | DataUriCollectionElementCollection;

export type DataUri = DataUriData | DataUriFile | DataUriCollection;

function isBaseDataUri(item: object): item is BaseDataUri {
    return Boolean(item) && ("url" in item || "location" in item);
}

export function isDataUriData(item: object): item is DataUriData {
    return isBaseDataUri(item) && "src" in item && item.src === "url";
}

export function isDataUriFile(item: object): item is DataUriFile {
    return (
        (isBaseDataUri(item) && ("class" in item || "class_" in item) && (item as DataUriFile).class === "File") ||
        (item as DataUriFile).class_ === "File"
    );
}

export function isDataUriCollection(item: object): item is DataUriCollection {
    return (
        (("class" in item || "class_" in item) && (item as DataUriCollection).class === "Collection") ||
        (item as DataUriCollection).class_ === "Collection"
    );
}

export function isDataUri(item: object): item is DataUri {
    return Boolean(item) && (isDataUriData(item) || isDataUriFile(item) || isDataUriCollection(item));
}

export function isDataUriCollectionElementCollection(
    item: DataUriCollectionElement
): item is DataUriCollectionElementCollection {
    return item.class === "Collection" || item.class_ === "Collection";
}

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

export function itemUniqueKey(item: DataOption): string {
    return `${item.src}-${item.id}`;
}

export function containsDataOption(items: DataOption[], item: DataOption | null): boolean {
    return item !== null && items.some((i) => itemUniqueKey(i) === itemUniqueKey(item));
}
