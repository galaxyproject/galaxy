import KNOWN_COLLECTION_TYPES_DATA from "./knownCollectionTypes.yml";

/** Where a collection type is being chosen: for a workflow input, or for a collection to build. */
export type CollectionTypeContext = "workflow_input" | "builder";

export interface KnownCollectionType {
    collectionType: string;
    label: string;
    description: string;
    notes: Partial<Record<CollectionTypeContext, string>>;
    group: string;
}

export interface KnownCollectionTypeGroup {
    group: string;
    types: KnownCollectionType[];
}

interface KnownCollectionTypeGroupData {
    group: string;
    types: {
        collection_type: string;
        label: string;
        description: string;
        notes?: Partial<Record<CollectionTypeContext, string>>;
    }[];
}

export const KNOWN_COLLECTION_TYPE_GROUPS: KnownCollectionTypeGroup[] = (
    KNOWN_COLLECTION_TYPES_DATA as KnownCollectionTypeGroupData[]
).map(({ group, types }) => ({
    group,
    types: types.map(({ collection_type, label, description, notes }) => ({
        collectionType: collection_type,
        label,
        description,
        notes: notes ?? {},
        group,
    })),
}));

export const KNOWN_COLLECTION_TYPES: KnownCollectionType[] = KNOWN_COLLECTION_TYPE_GROUPS.flatMap(({ types }) => types);

/** The known collection types in the order given; throws on a type the registry doesn't describe. */
export function findKnownCollectionTypes(collectionTypes: string[]): KnownCollectionType[] {
    return collectionTypes.map((collectionType) => {
        const known = KNOWN_COLLECTION_TYPES.find((known) => known.collectionType === collectionType);
        if (!known) {
            throw new Error(`No description for collection type ${collectionType}`);
        }
        return known;
    });
}

export function describeKnownCollectionType(known: KnownCollectionType, context: CollectionTypeContext): string {
    const note = known.notes[context];
    return note ? `${known.description} ${note}` : known.description;
}
