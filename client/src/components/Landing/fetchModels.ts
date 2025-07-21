import type {
    AnyFetchTarget,
    HdasUploadTarget,
    HdcaUploadTarget,
    NestedElement,
    NestedElementItem,
    UrlDataElement,
} from "@/api/tools";
import type { ParsedFetchWorkbookColumn, ParsedFetchWorkbookColumnType } from "@/components/Collections/wizard/types";
import { MAPPING_TARGETS } from "@/components/RuleBuilder/rule-definitions";

export type CellValueType = string | boolean | null;
export type RowType = Record<string, CellValueType>;
export type RowsType = RowType[];

// specify the order of column types to ensure consistent ordering
// for the table in the UI.
const canonicalColumnTypeOrder: ParsedFetchWorkbookColumnType[] = [
    "url",
    "list_identifiers",
    "paired_identifier",
    "paired_or_unpaired_identifier",
    "name",
    "deferred",
    "file_type",
    "dbkey",
    "tags",
    "info",
    "hash_sha1",
    "hash_md5",
    "hash_sha256",
    "hash_sha512",
    "to_posix_lines",
    "space_to_tab",
    "auto_decompress",
];

export class DerivedColumn implements ParsedFetchWorkbookColumn {
    type: ParsedFetchWorkbookColumnType;
    type_index: number;
    title: string;

    constructor(type: ParsedFetchWorkbookColumnType, typeIndex: number, title: string) {
        this.type = type;
        this.type_index = typeIndex;
        this.title = title;
    }

    key(): string {
        if (this.type_index > 0) {
            return `${this.type}_${this.type_index}`;
        } else {
            return this.type;
        }
    }
}

export interface FetchTable {
    columns: DerivedColumn[];
    rows: RowsType;
    isCollection: boolean;
    collectionType?: string;
    autoDecompress?: boolean;
}

function collectionTypeToColumns(collectionType: string | null | undefined): DerivedColumn[] {
    const columns: DerivedColumn[] = [];
    let listIdentifierCount = 0;
    // just make sure we're creating a simple type - don't let multiple paired or unpaired identifiers appear
    let pairedIdentifierCount = 0;
    if (collectionType) {
        const collectionTypeParts = collectionType.split(":");
        let ranksOfTypeList = 0;
        for (const collectionTypePart of collectionTypeParts) {
            if (collectionTypePart === "list") {
                ranksOfTypeList++;
            }
        }
        for (const collectionTypePart of collectionTypeParts) {
            if (collectionTypePart === "list") {
                let title = "List Identifier";
                if (ranksOfTypeList == 2) {
                    if (listIdentifierCount === 0) {
                        title = "Outer List Identifier";
                    } else if (listIdentifierCount === 1) {
                        title = "Inner List Identifier";
                    }
                } else if (ranksOfTypeList > 2) {
                    title = `List Identifier ${listIdentifierCount + 1}`;
                }
                const column = new DerivedColumn("list_identifiers", listIdentifierCount, title);
                listIdentifierCount++;
                columns.push(column);
            } else if (collectionTypePart === "paired" && pairedIdentifierCount === 0) {
                const column = new DerivedColumn("paired_identifier", 0, "Paired Identifier");
                pairedIdentifierCount++;
                columns.push(column);
            } else if (collectionTypePart === "paired_or_unpaired" && pairedIdentifierCount === 0) {
                const column = new DerivedColumn("paired_or_unpaired_identifier", 0, "Paired / Unpaired Identifier");
                pairedIdentifierCount++;
                columns.push(column);
            } else {
                throw Error(`Unsupported collection type part encountered: ${collectionTypePart}. `);
            }
        }
    }
    return columns;
}

function fetchTargetToTableColumns(
    target: AnyFetchTarget | NestedElementItem,
    isCollection: boolean = false
): DerivedColumn[] {
    const columns: DerivedColumn[] = [];

    function addColumnIfNew(column: DerivedColumn) {
        if (!columns.some((c) => c.type === column.type && c.type_index === column.type_index)) {
            columns.push(column);
        }
    }

    function toColumn(type: ParsedFetchWorkbookColumnType, typeIndex: number = 0): DerivedColumn {
        const titleBase = MAPPING_TARGETS[type].columnHeader || MAPPING_TARGETS[type].label || type;
        let title;
        if (typeIndex > 0) {
            title = `${titleBase} ${typeIndex + 1}`;
        } else {
            title = titleBase;
        }
        return new DerivedColumn(type, typeIndex, title);
    }

    function addDataElementColumn(item: UrlDataElement) {
        // TODO: handle deferred
        if (item.name && !isCollection) {
            addColumnIfNew(toColumn("name"));
        }
        if (item.MD5) {
            addColumnIfNew(toColumn("hash_md5"));
        }
        if (item["SHA-1"]) {
            addColumnIfNew(toColumn("hash_sha1"));
        }
        if (item["SHA-256"]) {
            addColumnIfNew(toColumn("hash_sha256"));
        }
        if (item["SHA-512"]) {
            addColumnIfNew(toColumn("hash_sha512"));
        }
        if (item.url) {
            addColumnIfNew(toColumn("url"));
        }
        if (item.ext) {
            addColumnIfNew(toColumn("file_type"));
        }
        if (item.dbkey) {
            addColumnIfNew(toColumn("dbkey"));
        }
        if (item.to_posix_lines) {
            addColumnIfNew(toColumn("to_posix_lines"));
        }
        if (item.space_to_tab) {
            addColumnIfNew(toColumn("space_to_tab"));
        }
        if (item.auto_decompress) {
            addColumnIfNew(toColumn("auto_decompress"));
        }
        if (item.tags && item.tags.length > 0) {
            let nameTagCount = 0;
            let groupTagCount = 0;
            let otherTagCount = 0;
            for (const tag of item.tags) {
                if (tag.startsWith("name:")) {
                    const nameTag = tag.substring(5);
                    if (nameTag) {
                        addColumnIfNew(toColumn("name_tag", nameTagCount++));
                    }
                } else if (tag.startsWith("group:")) {
                    const groupTag = tag.substring(6);
                    if (groupTag) {
                        addColumnIfNew(toColumn("group_tags", groupTagCount++));
                    }
                } else {
                    addColumnIfNew(toColumn("tags", otherTagCount++));
                }
            }
        }
    }

    if ("collection_type" in target && target.collection_type) {
        collectionTypeToColumns(target.collection_type).forEach((column) => {
            addColumnIfNew(column);
        });
    }
    if (!("elements" in target)) {
        throw Error("Unhandled fetch target type encountered.");
    } else {
        target.elements.forEach((value) => {
            const item = value as SupportedElementType;
            if ("src" in item && item.src === "url") {
                addDataElementColumn(item);
            } else if ("elements" in item) {
                const nestedItem: NestedElement = item;
                for (const column of fetchTargetToTableColumns(nestedItem, isCollection)) {
                    addColumnIfNew(column);
                }
            }
        });
    }

    // Sort columns by type, then by type_index
    columns.sort((a, b) => {
        let indexA = canonicalColumnTypeOrder.indexOf(a.type);
        let indexB = canonicalColumnTypeOrder.indexOf(b.type);
        if (indexA === -1) {
            indexA = 100;
        }
        if (indexB === -1) {
            indexB = 100;
        }

        if (indexA < indexB) {
            return -1;
        }
        if (indexA > indexB) {
            return 1;
        }
        return a.type_index - b.type_index;
    });
    return columns;
}

export function fetchTargetToRows(
    target: AnyFetchTarget | NestedElementItem,
    columns: DerivedColumn[],
    parentIdentifiers: string[]
): RowsType {
    const rows: RowsType = [];
    function addDataElementRow(item: UrlDataElement) {
        const row: RowType = {};
        for (const column of columns) {
            if (column.type == "list_identifiers") {
                row[column.key()] = parentIdentifiers[column.type_index] ?? item.name?.toString() ?? "";
            } else if (column.type === "paired_identifier") {
                row[column.key()] = parentIdentifiers[-1] ?? item.name?.toString() ?? "";
            } else if (column.type === "paired_or_unpaired_identifier") {
                row[column.key()] = parentIdentifiers[-1] ?? item.name?.toString() ?? "";
            } else if (column.type === "name") {
                if (item.name) {
                    row[column.key()] = item.name.toString();
                } else {
                    row[column.key()] = null;
                }
            } else if (column.type === "url") {
                if (item.url) {
                    row[column.key()] = item.url;
                } else {
                    throw Error("URL is required for data elements.");
                }
            } else if (column.type === "hash_md5") {
                if (item.MD5) {
                    row[column.key()] = item.MD5;
                } else {
                    row[column.key()] = null;
                }
            } else if (column.type === "hash_sha1") {
                if (item["SHA-1"]) {
                    row[column.key()] = item["SHA-1"];
                } else {
                    row[column.key()] = null;
                }
            } else if (column.type === "hash_sha256") {
                if (item["SHA-256"]) {
                    row[column.key()] = item["SHA-256"];
                } else {
                    row[column.key()] = null;
                }
            } else if (column.type === "hash_sha512") {
                if (item["SHA-512"]) {
                    row[column.key()] = item["SHA-512"];
                } else {
                    row[column.key()] = null;
                }
            } else if (column.type === "file_type") {
                if (item.ext) {
                    row[column.key()] = item.ext;
                } else {
                    row[column.key()] = null;
                }
            } else if (column.type === "dbkey") {
                if (item.dbkey) {
                    row[column.key()] = item.dbkey;
                } else {
                    row[column.key()] = "?";
                }
            } else if (column.type === "to_posix_lines") {
                row[column.key()] = item.to_posix_lines ? true : false;
            } else if (column.type === "space_to_tab") {
                row[column.key()] = item.space_to_tab ? true : false;
            } else if (column.type === "auto_decompress") {
                row[column.key()] = item.auto_decompress ? true : false;
            } else if (column.type === "name_tag") {
                if (item.tags && item.tags.length > 0) {
                    const nameTags = item.tags.filter((tag) => tag.startsWith("name:"));
                    if (nameTags.length > column.type_index) {
                        row[column.key()] = nameTags[column.type_index]!.substring(5);
                    } else {
                        row[column.key()] = null;
                    }
                } else {
                    row[column.key()] = null;
                }
            } else if (column.type === "group_tags") {
                if (item.tags && item.tags.length > 0) {
                    const groupTags = item.tags.filter((tag) => tag.startsWith("group:"));
                    if (groupTags.length > column.type_index) {
                        row[column.key()] = groupTags[column.type_index]!.substring(6);
                    } else {
                        row[column.key()] = null;
                    }
                } else {
                    row[column.key()] = null;
                }
            } else if (column.type === "tags") {
                if (item.tags && item.tags.length > 0) {
                    const genericTags = item.tags.filter(
                        (tag) => !tag.startsWith("group:") && !tag.startsWith("name:")
                    );
                    if (genericTags.length > column.type_index) {
                        row[column.key()] = genericTags[column.type_index]!;
                    } else {
                        row[column.key()] = null;
                    }
                } else {
                    row[column.key()] = null;
                }
            }
        }
        rows.push(row);
    }

    if (!("elements" in target)) {
        throw Error("Unhandled fetch target type encountered.");
    } else {
        target.elements.forEach((value) => {
            const item = value as SupportedElementType;
            if ("src" in item && item.src === "url") {
                addDataElementRow(item);
            } else if ("elements" in item) {
                const newParentIdentifiers = [...parentIdentifiers, item.name?.toString() ?? ""];
                fetchTargetToRows(item, columns, newParentIdentifiers).forEach((row) => {
                    rows.push(row);
                });
            }
        });
    }
    return rows;
}

export function fetchTargetToTable(target: AnyFetchTarget): FetchTable {
    const isCollection = "collection_type" in target;
    const collectionType: string | undefined = isCollection ? target.collection_type || undefined : undefined;
    const columns = fetchTargetToTableColumns(target, isCollection);
    const rows: RowsType = fetchTargetToRows(target, columns, []);
    return { columns, rows, isCollection, collectionType, autoDecompress: target.auto_decompress };
}

export type SupportedElementType = UrlDataElement | NestedElement;

function cellValue(
    table: FetchTable,
    rowIndex: number,
    columnType: ParsedFetchWorkbookColumnType,
    columnTypeIndex: number = 0
): CellValueType {
    const columnKey = new DerivedColumn(columnType, columnTypeIndex, "").key();
    const row = table.rows[rowIndex] as RowType;
    const value = row[columnKey];
    if (value === undefined) {
        throw Error(`Error processing table - somehow data is not as expected.`);
    }
    return value;
}

function nestedItemWithIdentifier(elements: SupportedElementType[], identifier: string): SupportedElementType {
    const nestedElementIndex = elements.findIndex((e) => e.name === identifier);
    if (nestedElementIndex === -1) {
        // type hack here to circumvent poor generation of type from API, do not
        // want to force specify a bunch of unspecified properties on the nested element
        const newNestedElement: SupportedElementType = {
            name: identifier,
        } as unknown as SupportedElementType;
        elements.push(newNestedElement);
        return newNestedElement;
    } else {
        return elements[nestedElementIndex] as NestedElement;
    }
}

function fillUrlElementForRow(element: UrlDataElement, table: FetchTable, rowIndex: number) {
    for (const column of table.columns) {
        if (column.type === "name") {
            element.name = cellValue(table, rowIndex, "name") ?? undefined;
        } else if (column.type === "url") {
            element.url = cellValue(table, rowIndex, "url") as string;
        } else if (column.type === "hash_md5") {
            element.MD5 = cellValue(table, rowIndex, "hash_md5") as string | null;
        } else if (column.type === "hash_sha1") {
            element["SHA-1"] = cellValue(table, rowIndex, "hash_sha1") as string | null;
        } else if (column.type === "hash_sha256") {
            element["SHA-256"] = cellValue(table, rowIndex, "hash_sha256") as string | null;
        } else if (column.type === "hash_sha512") {
            element["SHA-512"] = cellValue(table, rowIndex, "hash_sha512") as string | null;
        } else if (column.type === "file_type") {
            element.ext = cellValue(table, rowIndex, "file_type")?.toString() || "auto";
        } else if (column.type === "dbkey") {
            element.dbkey = cellValue(table, rowIndex, "dbkey")?.toString() || "?";
        } else if (column.type === "to_posix_lines") {
            element.to_posix_lines = cellValue(table, rowIndex, "to_posix_lines") === true;
        } else if (column.type === "space_to_tab") {
            element.space_to_tab = cellValue(table, rowIndex, "space_to_tab") === true;
        } else if (column.type === "auto_decompress") {
            element.auto_decompress = cellValue(table, rowIndex, "auto_decompress") === true;
        } else if (column.type === "name_tag") {
            const nameTag = cellValue(table, rowIndex, "name_tag", column.type_index);
            if (nameTag) {
                element.tags = element.tags || [];
                element.tags.push(`name:${nameTag}`);
            }
        } else if (column.type === "group_tags") {
            const groupTag = cellValue(table, rowIndex, "group_tags", column.type_index);
            if (groupTag) {
                element.tags = element.tags || [];
                element.tags.push(`group:${groupTag}`);
            }
        } else if (column.type === "tags") {
            const tag = cellValue(table, rowIndex, "tags", column.type_index);
            if (tag) {
                element.tags = element.tags || [];
                element.tags.push(tag.toString());
            }
        }
    }
}

function fillNestedElementForRow(
    elements: SupportedElementType[],
    table: FetchTable,
    rowIndex: number,
    collectionTypeParts: string[],
    currentCollectionTypePartIndex: number
) {
    const collectionTypePart = collectionTypeParts[currentCollectionTypePartIndex];
    let identifier: string;
    if (collectionTypePart === "list") {
        identifier = cellValue(table, rowIndex, "list_identifiers", currentCollectionTypePartIndex) as string;
    } else if (collectionTypePart === "paired") {
        identifier = cellValue(table, rowIndex, "paired_identifier", currentCollectionTypePartIndex) as string;
    } else if (collectionTypePart === "paired_or_unpaired") {
        identifier = cellValue(
            table,
            rowIndex,
            "paired_or_unpaired_identifier",
            currentCollectionTypePartIndex
        ) as string;
    } else {
        throw Error(`Unsupported collection type part encountered: ${collectionTypePart}.`);
    }
    const nestedElement = nestedItemWithIdentifier(elements, identifier);
    if (currentCollectionTypePartIndex < collectionTypeParts.length - 1) {
        const nestedNestedElement = nestedElement as NestedElement;
        nestedNestedElement.elements = nestedNestedElement.elements ?? [];
        fillNestedElementForRow(
            nestedNestedElement.elements as SupportedElementType[],
            table,
            rowIndex,
            collectionTypeParts,
            currentCollectionTypePartIndex + 1
        );
    } else {
        fillUrlElementForRow(nestedElement as UrlDataElement, table, rowIndex);
    }
}

function tableRowsToUrlElements(fetchTable: FetchTable): SupportedElementType[] {
    const items: SupportedElementType[] = [];
    const isCollection = fetchTable.isCollection;
    if (isCollection) {
        const collectionType = fetchTable.collectionType || null;
        const collectionTypeParts = collectionType ? collectionType.split(":") : [];
        for (let rowIndex = 0; rowIndex < fetchTable.rows.length; rowIndex++) {
            fillNestedElementForRow(items, fetchTable, rowIndex, collectionTypeParts, 0);
        }
    } else {
        for (let rowIndex = 0; rowIndex < fetchTable.rows.length; rowIndex++) {
            const urlElement = {
                src: "url",
            } as unknown as UrlDataElement;
            fillUrlElementForRow(urlElement, fetchTable, rowIndex);
            items.push(urlElement);
        }
    }
    return items;
}

export type SupportedRequestTarget = HdasUploadTarget | HdcaUploadTarget;

export function tableToRequest(fetchTable: FetchTable): SupportedRequestTarget {
    const elements = tableRowsToUrlElements(fetchTable);
    const autoDecompress = fetchTable.autoDecompress;
    if (fetchTable.isCollection) {
        return {
            collection_type: fetchTable.collectionType || null,
            elements: elements,
            auto_decompress: autoDecompress,
            destination: { type: "hdca" },
        } as HdcaUploadTarget;
    } else {
        return {
            destination: { type: "hdas" },
            elements: elements,
            auto_decompress: autoDecompress,
        } as HdasUploadTarget;
    }
}
