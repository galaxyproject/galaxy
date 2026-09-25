import type { TableField } from "@/components/Common/GTable.types";

export interface TabularMetadata {
    metadata_column_names?: Array<string>;
    metadata_columns?: number;
    metadata_delimiter?: string;
}

export function getFields(metaData: TabularMetadata): TableField[] {
    const fields: TableField[] = [];
    const columnNames = metaData.metadata_column_names || [];
    const columnCount = metaData.metadata_columns || 0;
    for (let i = 0; i < columnCount; i++) {
        fields.push({
            key: `${i}`,
            label: columnNames[i] || String(i),
            sortable: true,
        });
    }
    return fields;
}

export function getItems(textData: string, metaData: TabularMetadata): Record<string, string>[] {
    const tableData: Record<string, string>[] = [];
    const delimiter = metaData.metadata_delimiter || "\t";
    const lines = textData.split("\n");
    lines.forEach((line) => {
        // Galaxy counts blank lines and `#`-prefixed lines as "comment lines" (see
        // tabular.py's set_meta), so skip them the same way instead of slicing off
        // a fixed number of lines from the start.
        if (!line || line.startsWith("#")) {
            return;
        }
        const tabs = line.split(delimiter);
        const rowData: Record<string, string> = {};
        let hasData = false;
        tabs.forEach((cellData, j) => {
            const cellDataTrimmed = cellData.trim();
            if (cellDataTrimmed) {
                hasData = true;
            }
            rowData[j] = cellDataTrimmed;
        });
        if (hasData) {
            tableData.push(rowData);
        }
    });
    return tableData;
}
