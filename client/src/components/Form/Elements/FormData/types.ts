export interface DataOption {
    id: string;
    is_dataset?: boolean;
    keep: boolean;
    hid: number;
    map_over_type?: string;
    name: string;
    src: string;
    tags: Array<string>;
}
