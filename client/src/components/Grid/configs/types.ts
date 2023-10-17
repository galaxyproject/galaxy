type Field = FieldKey | FieldOperations;

interface FieldKey {
    key: string;
    type: string;
}

interface FieldOperations {
    title: string;
    operations: Array<Operation>;
}

interface HandlerMessage {
    message: string;
    status: string;
}

type HandlerReturn = HandlerMessage | void;

export interface Config {
    url: string;
    resource: string;
    item: string;
    plural: string;
    title: string;
    fields: Array<Field>;
}

export type RowData = Record<string, unknown>;

export interface Operation {
    title: string;
    handler: (data: RowData, router: any) => HandlerReturn;
}
