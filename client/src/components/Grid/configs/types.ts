import { IconDefinition } from "@fortawesome/fontawesome-svg-core";

import type { GalaxyConfiguration } from "@/stores/configurationStore";
import Filtering from "@/utils/filtering";

export interface Action {
    title: string;
    icon?: IconDefinition;
    handler: () => void;
}

export type ActionArray = Array<Action>;

export interface GridConfig {
    id: string;
    actions?: ActionArray;
    fields: FieldArray;
    filtering: Filtering<any>;
    getData: (offset: number, limit: number, search: string, sort_by: string, sort_desc: boolean) => Promise<any>;
    batch?: BatchOperationArray;
    plural: string;
    sortBy: string;
    sortKeys: Array<string>;
    sortDesc: boolean;
    title: string;
}

export type FieldArray = Array<FieldEntry>;

export interface FieldEntry {
    key: string;
    title: string;
    condition?: (data: RowData) => boolean;
    disabled?: boolean;
    type: validTypes;
    operations?: Array<Operation>;
    handler?: FieldHandler;
    width?: number;
}

export type FieldHandler = (data: RowData) => void;

export interface BatchOperation {
    title: string;
    icon: IconDefinition;
    condition?: (data: Array<RowData>) => boolean;
    handler: (data: Array<RowData>) => OperationHandlerReturn;
}

export type BatchOperationArray = Array<BatchOperation>;

export interface Operation {
    title: string;
    icon: IconDefinition;
    condition?: (data: RowData, config: GalaxyConfiguration) => boolean;
    handler: (data: RowData) => OperationHandlerReturn;
}

interface OperationHandlerMessage {
    message: string;
    status: string;
}

type OperationHandlerReturn = Promise<OperationHandlerMessage | undefined> | void;

export type RowData = Record<string, unknown>;

type validTypes = "boolean" | "date" | "datasets" | "link" | "operations" | "sharing" | "tags" | "text";
