export interface Config {
    url: string;
    resource: string;
    item: string;
    plural: string;
    title: string;
    fields: Array<Record<string, unknown>>;
}

interface HandlerMessage {
    message: string;
    status: string;
}

export type HandlerReturn = HandlerMessage | undefined;

export type RowData = Record<string, unknown>;

export interface Operation {
    title: string;
    handler: (data: RowData, router: any) => HandlerReturn;
}
