/**
 * The Uri types here are based on `DataOrCollectionRequest` defined in
 * `lib/galaxy/tool_util_models/parameters.py`.
 */
import type { FieldDict, SampleSheetColumnDefinition } from "@/api";

interface DatasetHash {
    hash_function: "MD5" | "SHA-1" | "SHA-256" | "SHA-512";
    hash_value: string;
}

interface BaseDataUri {
    location: string;
    name?: string | null;
    ext: string;
    dbkey?: string;
    deferred?: boolean;
    created_from_basename?: string | null;
    info?: string | null;
    hashes?: DatasetHash[] | null;
    space_to_tab?: boolean;
    to_posix_lines?: boolean;
}

interface DataUriData extends BaseDataUri {
    src: "url";
}

interface DataUriFile extends BaseDataUri {
    class: "File";
}

export interface DataUriCollectionElementFile extends DataUriFile {
    identifier: string;
}

export interface DataUriCollectionElementCollection {
    class: "Collection";
    identifier: string;
    collection_type: string;
    elements: DataUriCollectionElement[];
}

interface DataUriCollection {
    class: "Collection";
    collection_type: string;
    elements: DataUriCollectionElement[];
    deferred?: boolean;
    name?: string | null;
}

export type DataUriCollectionElement = DataUriCollectionElementFile | DataUriCollectionElementCollection;

export type DataUri = DataUriData | DataUriFile | DataUriCollection;

function isBaseDataUri(item: object): item is BaseDataUri {
    return Boolean(item) && "location" in item && "ext" in item;
}

export function isDataUriData(item: object): item is DataUriData {
    return isBaseDataUri(item) && "src" in item && item.src === "url";
}

export function isDataUriFile(item: object): item is DataUriFile {
    return isBaseDataUri(item) && "class" in item && item.class === "File";
}

export function isDataUriCollection(item: object): item is DataUriCollection {
    return Boolean(item) && "class" in item && item.class === "Collection" && "elements" in item;
}

export function isDataUri(item: object): item is DataUri {
    return Boolean(item) && (isDataUriData(item) || isDataUriFile(item) || isDataUriCollection(item));
}

export function isDataUriCollectionElementCollection(
    item: DataUriCollectionElement
): item is DataUriCollectionElementCollection {
    return item.class === "Collection";
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

export type ExtendedCollectionType = {
    columnDefinitions?: SampleSheetColumnDefinition[] | undefined;
    fields?: FieldDict[] | undefined;
};
