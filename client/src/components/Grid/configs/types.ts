type Field = FieldKey | FieldOperations;

interface FieldKey {
    key: string;
    type: string;
    handler?: FieldKeyHandler;
}

interface FieldOperations {
    title: string;
    operations: Array<Operation>;
}

interface OperationHandlerMessage {
    message: string;
    status: string;
}

type OperationHandlerReturn = OperationHandlerMessage | void;

export interface Config {
    url: string;
    resource: string;
    item: string;
    plural: string;
    title: string;
    fields: Array<Field>;
}

export type FieldKeyHandler = (data: RowData) => void;

export type RowData = Record<string, unknown>;

export interface Operation {
    title: string;
    handler: (data: RowData, router: any) => OperationHandlerReturn;
}
