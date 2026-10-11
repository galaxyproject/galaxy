import KNOWN_COLLECTION_TYPES_DATA from "./knownCollectionTypes.yml";

/** Where a collection type is being chosen: for a workflow input, or for a collection to build. */
export type CollectionTypeContext = "workflow_input" | "builder";

/** Names a collection and its elements, e.g. "a list with 4 pairs". */
export interface CollectionTypeSummary {
    container: string;
    element: string;
    elementPlural: string;
}

export interface KnownCollectionType {
    collectionType: string;
    label: string;
    shortLabel: string;
    summary: CollectionTypeSummary;
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
        short_label: string;
        summary: { container: string; element: string; element_plural: string };
        description: string;
        notes?: Partial<Record<CollectionTypeContext, string>>;
    }[];
}

export const KNOWN_COLLECTION_TYPE_GROUPS: KnownCollectionTypeGroup[] = (
    KNOWN_COLLECTION_TYPES_DATA as KnownCollectionTypeGroupData[]
).map(({ group, types }) => ({
    group,
    types: types.map(({ collection_type, label, short_label, summary, description, notes }) => ({
        collectionType: collection_type,
        label,
        shortLabel: short_label,
        summary: { container: summary.container, element: summary.element, elementPlural: summary.element_plural },
        description,
        notes: notes ?? {},
        group,
    })),
}));

export const KNOWN_COLLECTION_TYPES: KnownCollectionType[] = KNOWN_COLLECTION_TYPE_GROUPS.flatMap(({ types }) => types);

/** Lowercase names for running text, e.g. "Create a new list of pairs". */
export const COLLECTION_TYPE_SHORT_LABELS: Record<string, string> = Object.fromEntries(
    KNOWN_COLLECTION_TYPES.map((known) => [known.collectionType, known.shortLabel]),
);

/** The registry's entry for a collection type, if it describes one. */
export function findKnownCollectionType(collectionType: string): KnownCollectionType | undefined {
    return KNOWN_COLLECTION_TYPES.find((known) => known.collectionType === collectionType);
}

/** The known collection types in the order given; throws on a type the registry doesn't describe. */
export function findKnownCollectionTypes(collectionTypes: string[]): KnownCollectionType[] {
    return collectionTypes.map((collectionType) => {
        const known = findKnownCollectionType(collectionType);
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
