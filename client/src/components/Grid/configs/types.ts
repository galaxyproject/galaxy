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
    getUrl: (currentPage: number, perPage: number, sortBy: string, sortDesc: boolean, search: string) => string;
    resource: string;
    item: string;
    plural: string;
    title: string;
    fields: Array<Field>;
    sortBy: string;
    sortKeys: Array<string>;
    filterClass: Filtering<string>;
    sortDesc: boolean;
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
    handler: (data: RowData, router: any) => OperationHandlerReturn;
}
