/**
 * The Uri types here are based on `DataOrCollectionRequest` defined in
 * `lib/galaxy/tool_util_models/parameters.py`.
 */
import type { FieldDict, SampleSheetColumnDefinition } from "@/api";

/**
 * Options fetched per page. Mirrors ``DEFAULT_OPTIONS_PAGE_SIZE`` in
 * ``galaxy.tools.parameters.pagination``, which sizes the first page the
 * server renders into a data parameter.
 */
export const DEFAULT_OPTIONS_PAGE_SIZE = 50;

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
    item: DataUriCollectionElement,
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
    column_definitions?: SampleSheetColumnDefinition[] | null;
};

export function isDataOption(item: object): item is DataOption {
    return !!item && "src" in item;
}

type OptionIdentity = Pick<DataOption, "id" | "src" | "map_over_type">;

/** Identifies an option; an item listed both directly and mapped over yields two distinct keys */
export function itemUniqueKey(item: OptionIdentity): string {
    const key = `${item.src}-${item.id}`;
    return item.map_over_type ? `${key}-${item.map_over_type}` : key;
}

export function containsDataOption(items: DataOption[], item: DataOption | null): boolean {
    return item !== null && items.some((i) => itemUniqueKey(i) === itemUniqueKey(item));
}

/** Whether two options refer to the same history item, however each is mapped over */
export function isSameItem(a: OptionIdentity, b: OptionIdentity): boolean {
    return a.id === b.id && a.src === b.src;
}

/**
 * Find the option for a value: the entry mapped over the same way, else any entry for the same item.
 * Values without a map-over type resolve to the first (direct) entry.
 */
export function findDataOption<T>(
    items: T[],
    value: OptionIdentity,
    toOption: (item: T) => DataOption | null | undefined,
): T | undefined {
    const key = itemUniqueKey(value);
    return (
        items.find((item) => {
            const option = toOption(item);
            return !!option && itemUniqueKey(option) === key;
        }) ??
        items.find((item) => {
            const option = toOption(item);
            return !!option && isSameItem(option, value);
        })
    );
}

/** Append a fetched page of options, skipping ones already listed */
export function mergeDataOptions(existing: DataOption[], incoming: DataOption[]): DataOption[] {
    const seen = new Set(existing.map(itemUniqueKey));
    return existing.concat(
        incoming.filter((option) => {
            const key = itemUniqueKey(option);
            if (seen.has(key)) {
                return false;
            }
            seen.add(key);
            return true;
        }),
    );
}

export type ExtendedCollectionType = {
    columnDefinitions?: SampleSheetColumnDefinition[] | undefined;
    fields?: FieldDict[] | undefined;
};
