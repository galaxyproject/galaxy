export interface DataOption {
    id: string;
    hid: number;
    is_dataset?: boolean;
    keep: boolean;
    map_over_type?: string;
    name: string;
    src: string;
    tags: Array<string>;
}
