import type { components } from "@/api/schema";

export type RulesCreatingWhat = "datasets" | "collections";
export type RulesSourceFrom = "remote_files" | "pasted_table" | "dataset_as_table" | "collection";

export type ListUriResponse = components["schemas"]["ListUriResponse"];
export type RemoteFile = components["schemas"]["RemoteFile"];
export type RemoteDirectory = components["schemas"]["RemoteDirectory"];

export type RawRowData = string[][];
export type InitialElements = RawRowData | HDCADetailed;

// types and helpers around initializing the rule builder with data
export type RuleSelectionType = "raw" | "remote_files";
export type RuleElementsType = RemoteFile[] | string[][];

// it would be nice to have a real type from the rule builder but
// it is older code. This is really outlining what this component can
// produce and not what the rule builder can consume which is a wide
// superset of this.
export interface RuleBuilderOptions {
    dataType: RulesCreatingWhat;
    ftpUploadSite?: string;
    elements?: RuleElementsType | undefined;
    content?: string;
    selectionType: RuleSelectionType;
}
