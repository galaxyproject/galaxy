import { type components } from "@/api/schema";

export type FileSourceTemplateSummary = components["schemas"]["FileSourceTemplateSummary"];
export type FileSourceTemplateSummaries = FileSourceTemplateSummary[];

export type UserFileSourceModel = components["schemas"]["UserFileSourceModel"];
export type FileSourceTypes = UserFileSourceModel["type"];
