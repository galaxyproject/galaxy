export interface DataOption {
    id: string;
    keep: boolean;
    hid: number;
    hda?: boolean;
    map_over_type?: string;
    name: string;
    src: string;
    tags: Array<string>;
}
