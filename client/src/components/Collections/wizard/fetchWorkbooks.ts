// utilities for populating the rule builder from parsed "fetch workbook"s.
import type {
    ColumnMappingType,
    ParsedFetchWorkbook,
    ParsedFetchWorkbookColumn,
    RawRowData,
    RuleBuilderMapping,
    RulesCreatingWhat,
} from "./types";

export function hasData(parsedWorkbook: ParsedFetchWorkbook): boolean {
    return parsedWorkbook.rows.length > 0;
}

export interface ForBuilderResponse {
    initialElements: string[][];
    rulesCreatingWhat: RulesCreatingWhat;
    initialMapping: RuleBuilderMapping;
}

export function forBuilder(parsedWorkbook: ParsedFetchWorkbook): ForBuilderResponse {
    const initialElements: RawRowData = [];
    const rulesCreatingWhat = creatingWhat(parsedWorkbook);
    for (const row of parsedWorkbook.rows) {
        const rowAsString: string[] = [];
        for (const column of parsedWorkbook.columns) {
            const rowKey: string = columnToRowKey(column);
            const cellValue = row[rowKey];
            if (cellValue === undefined) {
                throw Error("Error processing server response.");
            }
            rowAsString.push(cellValue || "");
        }
        initialElements.push(rowAsString);
    }
    const initialMapping = buildInitialMapping(parsedWorkbook);
    return {
        initialElements,
        initialMapping,
        rulesCreatingWhat,
    };
}

function columnToRowKey(column: ParsedFetchWorkbookColumn): string {
    if (column.type_index == 0) {
        return column.type;
    } else {
        return `${column.type}_${column.type_index}`;
    }
}

function creatingWhat(parsedWorkbook: ParsedFetchWorkbook): RulesCreatingWhat {
    if (parsedWorkbook.workbook_type == "datasets") {
        return "datasets";
    } else {
        return "collections";
    }
}

function buildInitialMapping(parsedWorkbook: ParsedFetchWorkbook): RuleBuilderMapping {
    const columnMappings: RuleBuilderMapping = [];
    for (let index = 0; index < parsedWorkbook.columns.length; index++) {
        const column = parsedWorkbook.columns[index] as ParsedFetchWorkbookColumn;
        const type: ColumnMappingType = column.type;
        if (column.type_index > 0) {
            for (const columnMapping of columnMappings) {
                if (columnMapping.type == type) {
                    columnMapping.columns.push(index);
                }
            }
        } else {
            columnMappings.push({
                type: type,
                columns: [index],
            });
        }
    }
    return columnMappings;
}

const COLUMN_TITLE_PREFIXES: Record<string, ColumnMappingType> = {
    name: "name",
    listname: "collection_name",
    collectionname: "collection_name",
    uri: "url",
    url: "url",
    urldeferred: "url_deferred",
    deferredurl: "url_deferred",
    genome: "dbkey",
    dbkey: "dbkey",
    filetype: "file_type",
    extension: "file_type",
    info: "info",
    tag: "tags",
    grouptag: "group_tags",
    nametag: "name_tag",
    listidentifier: "list_identifiers",
    pairedidentifier: "paired_identifier",
    hashmd5sum: "hash_md5",
    hashmd5: "hash_md5",
    md5sum: "hash_md5",
    md5: "hash_md5",
    sha1hash: "hash_sha1",
    hashsha1sum: "hash_sha1",
    hashsha1: "hash_sha1",
    sha1sum: "hash_sha1",
    sha1: "hash_sha1",
    sha256hash: "hash_sha256",
    hashsha256sum: "hash_sha256",
    hashsha256: "hash_sha256",
    sha256sum: "hash_sha256",
    sha256: "hash_sha256",
    sha512hash: "hash_sha512",
    hashsha512sum: "hash_sha512",
    hashsha512: "hash_sha512",
    sha512sum: "hash_sha512",
    sha512: "hash_sha512",
};

export function columnTitleToTargetType(columnTitle: string): ColumnMappingType | undefined {
    let normalizedTitle = columnTitle.toLowerCase().replace(/[\s()\-_]|optional/g, "");
    if (!(normalizedTitle in COLUMN_TITLE_PREFIXES)) {
        for (const key of Object.keys(COLUMN_TITLE_PREFIXES)) {
            if (normalizedTitle.startsWith(key) || normalizedTitle.endsWith(key)) {
                normalizedTitle = key;
                break;
            }
        }
    }

    if (!(normalizedTitle in COLUMN_TITLE_PREFIXES)) {
        return undefined;
    }

    return COLUMN_TITLE_PREFIXES[normalizedTitle] as string;
}
