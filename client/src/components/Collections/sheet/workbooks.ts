import { GalaxyApi, type SampleSheetColumnDefinition, type SampleSheetColumnDefinitions } from "@/api";
import { createWorkbook, createWorkbookForCollection, type SampleSheetCollectionType } from "@/api/datasetCollections";
import { stripExtension } from "@/components/Collections/common/stripExtension";
import type { PrefixColumnsType } from "@/components/Collections/wizard/types";

export async function downloadWorkbook(
    columnDefinitions: SampleSheetColumnDefinitions,
    collectionType: SampleSheetCollectionType,
    initialRows?: string[][]
) {
    if (!columnDefinitions) {
        return;
    }
    try {
        const workbookBlob = await createWorkbook({
            // why does the API schema think title is required?
            title: "Sample Sheet Workbook",
            prefix_columns_type: "URI",
            column_definitions: columnDefinitions,
            collection_type: collectionType,
            prefix_values: initialRows,
        });
        createAndClickDownloadLink(workbookBlob, "sample_sheet_workbook.xlsx");
    } catch (error) {
        // TODO: handle error better
        console.error("Error downloading workbook:", error);
    }
}

export async function downloadWorkbookForCollection(columnDefinitions: SampleSheetColumnDefinitions, hdca_id: string) {
    if (!columnDefinitions) {
        return;
    }

    try {
        const workbookBlob = await createWorkbookForCollection(hdca_id, {
            column_definitions: columnDefinitions,
        });
        createAndClickDownloadLink(workbookBlob, "sample_sheet_workbook.xlsx");
    } catch (error) {
        // TODO: handle error better
        console.error("Error downloading workbook:", error);
    }
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

function createAndClickDownloadLink(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename); // Set the desired filename for the download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link); // Clean up the temporary link
    window.URL.revokeObjectURL(url); // Release the object URL
}
