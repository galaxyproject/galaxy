import type { components } from "@/api/schema";
import type { MAPPING_TARGETS } from "@/components/RuleBuilder/rule-definitions";

export type RulesCreatingWhat = "datasets" | "collections";
export type RulesSourceFrom = "remote_files" | "pasted_table" | "dataset_as_table" | "collection" | "workbook";

export type ListUriResponse = components["schemas"]["ListUriResponse"];
export type RemoteFile = components["schemas"]["RemoteFile"];
export type RemoteDirectory = components["schemas"]["RemoteDirectory"];
export type ParsedFetchWorkbookForCollections = components["schemas"]["ParsedFetchWorkbookForCollections"];
export type ParsedFetchWorkbookForDatasets = components["schemas"]["ParsedFetchWorkbookForDatasets"];
export type ParsedFetchWorkbook = ParsedFetchWorkbookForCollections | ParsedFetchWorkbookForDatasets;
export type ParsedFetchWorkbookColumn = components["schemas"]["ParsedColumn"];
export type ParsedFetchWorkbookForCollectionCollectionType =
    components["schemas"]["ParsedFetchWorkbookForCollections"]["collection_type"];

export type RawRowData = string[][];

// types and helpers around initializing the rule builder with data
export type RuleSelectionType = "raw" | "remote_files";
export type RuleElementsType = RemoteFile[] | string[][];
export type ColumnMappingType = keyof typeof MAPPING_TARGETS;
export type ParsedFetchWorkbookColumnType = ParsedFetchWorkbookColumn["type"];

export interface RuleBuilderSingleMapping {
    type: ColumnMappingType;
    columns: number[];
}
export type RuleBuilderMapping = RuleBuilderSingleMapping[];

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
    initialMappings?: RuleBuilderMapping;
}
