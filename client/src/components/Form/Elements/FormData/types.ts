export type DataOption = {
    id: string;
    hid: number;
    is_dataset?: boolean;
    keep: boolean;
    batch: boolean;
    map_over_type?: string;
    name: string;
    src: string;
    tags: Array<string>;
};

export function isDataOption(item: object): item is DataOption {
    return !!item && "src" in item;
}
