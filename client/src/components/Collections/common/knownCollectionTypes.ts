import KNOWN_COLLECTION_TYPES_DATA from "./knownCollectionTypes.yml";

export interface KnownCollectionType {
    collectionType: string;
    label: string;
    description: string;
    group: string;
}

export interface KnownCollectionTypeGroup {
    group: string;
    types: KnownCollectionType[];
}

interface KnownCollectionTypeGroupData {
    group: string;
    types: { collection_type: string; label: string; description: string }[];
}

export const KNOWN_COLLECTION_TYPE_GROUPS: KnownCollectionTypeGroup[] = (
    KNOWN_COLLECTION_TYPES_DATA as KnownCollectionTypeGroupData[]
).map(({ group, types }) => ({
    group,
    types: types.map(({ collection_type, label, description }) => ({
        collectionType: collection_type,
        label,
        description,
        group,
    })),
}));

export const KNOWN_COLLECTION_TYPES: KnownCollectionType[] = KNOWN_COLLECTION_TYPE_GROUPS.flatMap(({ types }) => types);
