import { type components } from "@/api/schema";

export type RulesCreatingWhat = "datasets" | "collections";
export type RulesSourceFrom = "remote_files" | "pasted_table" | "dataset_as_table" | "collection";

export type ListUriResponse = components["schemas"]["ListUriResponse"];
export type RemoteFile = components["schemas"]["RemoteFile"];
export type RemoteDirectory = components["schemas"]["RemoteDirectory"];
