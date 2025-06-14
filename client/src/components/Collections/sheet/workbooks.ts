import { GalaxyApi, type SampleSheetColumnDefinition, type SampleSheetColumnDefinitions } from "@/api";
import type { SampleSheetCollectionType } from "@/api/datasetCollections";
import { stripExtension } from "@/components/Collections/common/stripExtension";
import type { PrefixColumnsType } from "@/components/Collections/wizard/types";
import { withPrefix } from "@/utils/redirect";

export function getDownloadWorkbookUrl(
    columnDefinitions: SampleSheetColumnDefinitions,
    collectionType: SampleSheetCollectionType,
    initialRows?: string[][]
) {
    const columnDefinitionsJson = JSON.stringify(columnDefinitions);
    const columnDefinitionsJsonBase64 = Buffer.from(columnDefinitionsJson).toString("base64");
    let url = withPrefix(
        `/api/sample_sheet_workbook/generate?collection_type=${collectionType}&column_definitions=${columnDefinitionsJsonBase64}`
    );
    if (initialRows) {
        const initialRowsJson = JSON.stringify(initialRows);
        const initialRowsJsonBase64 = Buffer.from(initialRowsJson).toString("base64");
        url = `${url}&prefix_values=${initialRowsJsonBase64}`;
    }
    return url;
}

export function getDownloadWorkbookUrlForCollection(column_definitions: SampleSheetColumnDefinitions, hdca_id: string) {
    const columnDefinitionsJson = JSON.stringify(column_definitions);
    const columnDefinitionsJsonBase64 = Buffer.from(columnDefinitionsJson).toString("base64");
    const url = withPrefix(
        `/api/dataset_collections/${hdca_id}/sample_sheet_workbook/generate?column_definitions=${columnDefinitionsJsonBase64}`
    );
    return url;
}

export function downloadWorkbook(
    columnDefinitions: SampleSheetColumnDefinitions,
    collectionType: SampleSheetCollectionType,
    initialRows?: string[][]
) {
    const url = getDownloadWorkbookUrl(columnDefinitions, collectionType, initialRows);
    window.location.assign(url);
}

export function downloadWorkbookForCollection(columnDefinitions: SampleSheetColumnDefinitions, hdca_id: string) {
    const url = getDownloadWorkbookUrlForCollection(columnDefinitions, hdca_id);
    window.location.assign(url);
}

export function initialValue(columnDefinition: SampleSheetColumnDefinition) {
    const defaultValue = columnDefinition.default_value;
    if (defaultValue === undefined) {
        switch (columnDefinition.type) {
            case "int":
                return columnDefinition.optional ? null : 0;
            case "float":
                return columnDefinition.optional ? null : 0.0;
            case "boolean":
                // TODO!!!
                return false;
            case "string":
            default:
                return "";
        }
    } else {
        return defaultValue;
    }
}

export function parseWorkbook(
    collectionType: SampleSheetCollectionType,
    columnDefinitions: SampleSheetColumnDefinitions | undefined,
    prefixColumnTypes: PrefixColumnsType,
    base64Content: string
) {
    const parseBody = {
        collection_type: collectionType,
        column_definitions: columnDefinitions || [],
        content: base64Content,
        prefix_columns_type: prefixColumnTypes,
    };
    return GalaxyApi().POST("/api/sample_sheet_workbook/parse", {
        body: parseBody,
    });
}

export function withAutoListIdentifiers(rows: string[][]): string[][] {
    const seenBasenames = new Map<string, number>();
    return rows.map((row) => {
        console.log(row);
        if (row.length === 1 && row[0]) {
            const uri = row[0];
            let basename = uri.split("/").pop() || uri;

            if (seenBasenames.has(basename)) {
                const count = seenBasenames.get(basename)! + 1;
                seenBasenames.set(basename, count);
                basename = `${basename}_${count}`;
            } else {
                seenBasenames.set(basename, 1);
            }

            return [uri, stripExtension(basename)];
        }
        return row;
    });
}
