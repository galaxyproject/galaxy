export type KnownCollectionTypeGroup = "Lists" | "Pairs and Records" | "Nested Lists" | "Sample Sheets";

export interface KnownCollectionType {
    collectionType: string;
    label: string;
    description: string;
    group: KnownCollectionTypeGroup;
}

export const KNOWN_COLLECTION_TYPE_GROUPS: KnownCollectionTypeGroup[] = [
    "Lists",
    "Pairs and Records",
    "Nested Lists",
    "Sample Sheets",
];

export const KNOWN_COLLECTION_TYPES: KnownCollectionType[] = [
    {
        collectionType: "list",
        label: "List of Datasets",
        description:
            "A simple flat list of datasets, each with an identifier (typically a sample name). If your data isn't nested and doesn't contain paired datasets, this is the option to choose.",
        group: "Lists",
    },
    {
        collectionType: "list:paired",
        label: "List of Dataset Pairs",
        description:
            "A list where every element is a forward and reverse pair of datasets (e.g. paired-end sequencing data from Illumina or Element Biosciences).",
        group: "Lists",
    },
    {
        collectionType: "list:paired_or_unpaired",
        label: "Mixed List of Paired and Unpaired Datasets",
        description:
            "A list where each element is either a single dataset or a forward and reverse pair. For studies with a mix of paired and unpaired data. Existing tools and workflows may need to be updated to handle this modality. A list of dataset pairs can also be connected to this input.",
        group: "Lists",
    },
    {
        collectionType: "list:record",
        label: "List of Records",
        description:
            "A list where every element is a record - a fixed set of named datasets (e.g. a sequence file and its index) declared by its record fields.",
        group: "Lists",
    },
    {
        collectionType: "paired",
        label: "Dataset Pair",
        description: "A single forward and reverse pair of datasets, such as the reads for one paired-end sample.",
        group: "Pairs and Records",
    },
    {
        collectionType: "record",
        label: "Record",
        description: "A single fixed set of named datasets, declared by its record fields.",
        group: "Pairs and Records",
    },
    {
        collectionType: "list:list",
        label: "Nested List of Datasets",
        description:
            "A list where each element is in turn a list of datasets. The outer identifier might group samples by condition, sample type, etc.",
        group: "Nested Lists",
    },
    {
        collectionType: "list:list:paired",
        label: "Nested List of Dataset Pairs",
        description: "A list where each element is in turn a list of forward and reverse dataset pairs.",
        group: "Nested Lists",
    },
    {
        collectionType: "sample_sheet",
        label: "Sample Sheet of Datasets",
        description:
            "A list of datasets where each element also carries a row of typed metadata (e.g. condition, replicate) described by its column definitions. Only sample sheets can be connected to a sample sheet input, but a sample sheet can be connected to a list input.",
        group: "Sample Sheets",
    },
    {
        collectionType: "sample_sheet:paired",
        label: "Sample Sheet of Dataset Pairs",
        description:
            "A list of forward and reverse dataset pairs where each pair also carries a row of typed metadata described by its column definitions.",
        group: "Sample Sheets",
    },
    {
        collectionType: "sample_sheet:paired_or_unpaired",
        label: "Sample Sheet of Paired and Unpaired Datasets",
        description:
            "A mix of single datasets and dataset pairs where each element also carries a row of typed metadata described by its column definitions.",
        group: "Sample Sheets",
    },
    {
        collectionType: "sample_sheet:record",
        label: "Sample Sheet of Records",
        description:
            "A list of records where each record also carries a row of typed metadata described by its column definitions.",
        group: "Sample Sheets",
    },
];

export function findKnownCollectionType(collectionType: string | null | undefined): KnownCollectionType | undefined {
    return KNOWN_COLLECTION_TYPES.find((known) => known.collectionType === collectionType);
}
