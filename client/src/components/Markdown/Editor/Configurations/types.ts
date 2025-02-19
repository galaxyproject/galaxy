export interface ApiResponse {
    data: Array<any> | undefined;
    error?: { err_msg: string };
}

export interface ContentType {
    dataset_id: string;
    dataset_name?: string;
}

export interface OptionType {
    id: string | null | undefined;
    name: string | null | undefined;
}
