import type { ExportParams } from "@/components/Common/models/exportRecordModel";

export type HistoryExportDestination = "download" | "remote-source" | "rdm-repository" | "zenodo-repository";

export interface HistoryExportData extends ExportParams {
    destination: HistoryExportDestination;
    remoteUri: string;
    outputFileName: string;
}
