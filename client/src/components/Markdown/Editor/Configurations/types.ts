export type ApiResponse = Array<any> | undefined;

export interface ContentType {
    dataset_id: string;
    dataset_name?: string;
}

export interface OptionType {
    id: string | null | undefined;
    name: string | null | undefined;
}
