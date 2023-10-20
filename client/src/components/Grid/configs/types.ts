type Field = FieldKey | FieldOperations;

// TODO: type FieldType = "date" | "operations" | "sharing" | "tags" | "text" | undefined;

interface FieldKey {
    key?: string;
    type: string;
    handler?: FieldKeyHandler;
}

interface OperationHandlerMessage {
    message: string;
    status: string;
}

type OperationHandlerReturn = OperationHandlerMessage | void;

export interface Config {
    getUrl: (currentPage: number, perPage: number, search: string) => string;
    resource: string;
    item: string;
    plural: string;
    title: string;
    fields: Array<Field>;
}

export interface FieldOperations {
    title: string;
    operations: Array<Operation>;
}

export type FieldKeyHandler = (data: RowData) => void;

export type RowData = Record<string, unknown>;

export interface Operation {
    title: string;
    handler: (data: RowData, router: any) => OperationHandlerReturn;
}
