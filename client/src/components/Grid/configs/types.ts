import type { AxiosResponse } from "axios";

import Filtering from "@/utils/filtering";

interface Action {
    title: string;
    icon?: string;
    handler: (router: any) => void;
}

type Field = FieldKey | FieldOperations;

interface FieldKey {
    key: string;
    type: string;
    handler?: FieldKeyHandler;
}

// TODO: Apply strict literals
// type FieldType = "date" | "operations" | "sharing" | "tags" | "text" | undefined;

interface OperationHandlerMessage {
    message: string;
    status: string;
}

type OperationHandlerReturn = OperationHandlerMessage | void;

/**
 * Exported Type declarations
 */
export interface Config {
    actions: Array<Action>;
    fields: Array<Field>;
    filtering: Filtering<string>;
    getData: (
        currentPage: number,
        perPage: number,
        sortBy: string,
        sortDesc: boolean,
        search: string
    ) => Promise<AxiosResponse>;
    item: string;
    plural: string;
    sortBy: string;
    sortKeys: Array<string>;
    sortDesc: boolean;
    title: string;
}

export interface FieldOperations {
    key: string;
    title: string;
    operations: Array<Operation>;
    width?: string;
}

export type FieldKeyHandler = (data: RowData) => void;

export type RowData = Record<string, unknown>;

export interface Operation {
    title: string;
    icon?: string;
    handler: (data: RowData, router: any) => OperationHandlerReturn;
}
