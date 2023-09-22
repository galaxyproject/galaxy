import { components } from "@/schema";

export type DatasetSummary = components["schemas"]["HDASummary"];
export type DatasetDetails = components["schemas"]["HDADetailed"];
export type DCESummary = components["schemas"]["DCESummary"];
export type HDCASummary = components["schemas"]["HDCASummary"];
export type HDCADetailed = components["schemas"]["HDCADetailed"];

export type HistoryContentItemBase = components["schemas"]["EncodedHistoryContentItem"];

export type DatasetEntry = DatasetSummary | DatasetDetails;
