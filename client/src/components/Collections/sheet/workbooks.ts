import { type SampleSheetColumnDefinitions } from "@/api";
import { withPrefix } from "@/utils/redirect";

export function getDownloadWorkbookUrl(columnDefinitions: SampleSheetColumnDefinitions, initialRows?: string[][]) {
    const columnDefinitionsJson = JSON.stringify(columnDefinitions);
    const columnDefinitionsJsonBase64 = Buffer.from(columnDefinitionsJson).toString("base64");
    let url = withPrefix(`/api/sample_sheet_workbook/generate?column_definitions=${columnDefinitionsJsonBase64}`);
    if (initialRows) {
        const initialRowsJson = JSON.stringify(initialRows);
        const initialRowsJsonBase64 = Buffer.from(initialRowsJson).toString("base64");
        url = `${url}&initial_rows=${initialRowsJsonBase64}`;
    }
    return url;
}

export function downloadWorkbook(columnDefinitions: SampleSheetColumnDefinitions, initialRows?: string[][]) {
    const url = getDownloadWorkbookUrl(columnDefinitions, initialRows);
    window.location.assign(url);
}
