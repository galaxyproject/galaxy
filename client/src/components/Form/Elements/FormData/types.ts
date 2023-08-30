export interface DataOption {
    id: string;
    hid: number;
    is_dataset?: boolean;
    keep: boolean;
    name: string;
    src: string;
    subcollection_type?: string;
    tags: Array<string>;
}
