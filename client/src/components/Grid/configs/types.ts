import type { AxiosResponse } from "axios";

import Filtering from "@/utils/filtering";

type Field = FieldKey | FieldOperations;

// TODO: type FieldType = "date" | "operations" | "sharing" | "tags" | "text" | undefined;

interface FieldKey {
    key: string;
    type: string;
    handler?: FieldKeyHandler;
}

interface OperationHandlerMessage {
    message: string;
    status: string;
}

type OperationHandlerReturn = OperationHandlerMessage | void;

export interface Config {
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
