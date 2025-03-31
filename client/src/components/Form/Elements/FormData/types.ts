type LandingDataFile = {
    class: "File";
    filetype: string;
    location: string;
};

type LandingDataCollection = {
    class: "Collection";
    collection_type: string;
    elements?: Array<LandingDataFileElement | LandingDataCollectionElement>;
};

export type LandingDataFileElement = {
    class: "File";
    identifier: string;
    location: string;
};

export type LandingDataCollectionElement = {
    class: "Collection";
    elements?: Array<LandingDataFileElement | LandingDataCollectionElement>;
    identifier: string;
    type: string;
};

export type LandingData = LandingDataFile | LandingDataCollection;

export type DataOption = {
    id: string;
    hid?: number;
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

export function itemUniqueKey(item: DataOption): string {
    return `${item.src}-${item.id}`;
}

export function containsDataOption(items: DataOption[], item: DataOption | null): boolean {
    return item !== null && items.some((i) => itemUniqueKey(i) === itemUniqueKey(item));
}

export function isLandingData(item: object): item is LandingData {
    return !!item && "class" in item && (item as LandingData).class !== undefined;
}
