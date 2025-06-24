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
