// ============================================================================
// plain 3 step job chain
var datasets1 = [
    { name: "SET1-01_1.fastq" },
    { name: "SET1-01_2.fastq" },
    { name: "SET1-02_1.fastq" },
    { name: "SET1-02_2.fastq" },
    { name: "SET1-03_1.fastq" },
    { name: "SET1-03_2.fastq" },
    { name: "SET1-04_1.fastq" },
    { name: "SET1-04_2.fastq" },
    { name: "SET1-05_1.fastq" },
    { name: "SET1-05_2.fastq" },
    { name: "SET1-06_1.fastq" },
    { name: "SET1-06_2.fastq" },
    { name: "SET1-07_1.fastq" },
    { name: "SET1-07_2.fastq" }
];

var datasets1CreateRequestJSON = {
    type: "dataset_collection",
    collection_type: "list:paired",
    name: "Heres a collection",
    hide_source_items: false,
    element_identifiers: [
        {
            collection_type: "paired",
            src: "new_collection",
            name: "SET1-07",
            element_identifiers: [
                {
                    name: "forward",
                    id: "2",
                    src: "hda"
                },
                {
                    name: "reverse",
                    id: "3",
                    src: "hda"
                }
            ]
        },
        {
            collection_type: "paired",
            src: "new_collection",
            name: "SET1-06",
            element_identifiers: [
                {
                    name: "forward",
                    id: "4",
                    src: "hda"
                },
                {
                    name: "reverse",
                    id: "5",
                    src: "hda"
                }
            ]
        },
        {
            collection_type: "paired",
            src: "new_collection",
            name: "SET1-05",
            element_identifiers: [
                {
                    name: "forward",
                    id: "6",
                    src: "hda"
                },
                {
                    name: "reverse",
                    id: "7",
                    src: "hda"
                }
            ]
        },
        {
            collection_type: "paired",
            src: "new_collection",
            name: "SET1-04",
            element_identifiers: [
                {
                    name: "forward",
                    id: "8",
                    src: "hda"
                },
                {
                    name: "reverse",
                    id: "9",
                    src: "hda"
                }
            ]
        },
        {
            collection_type: "paired",
            src: "new_collection",
            name: "SET1-03",
            element_identifiers: [
                {
                    name: "forward",
                    id: "10",
                    src: "hda"
                },
                {
                    name: "reverse",
                    id: "11",
                    src: "hda"
                }
            ]
        },
        {
            collection_type: "paired",
            src: "new_collection",
            name: "SET1-02",
            element_identifiers: [
                {
                    name: "forward",
                    id: "12",
                    src: "hda"
                },
                {
                    name: "reverse",
                    id: "13",
                    src: "hda"
                }
            ]
        },
        {
            collection_type: "paired",
            src: "new_collection",
            name: "SET1-01",
            element_identifiers: [
                {
                    name: "forward",
                    id: "14",
                    src: "hda"
                },
                {
                    name: "reverse",
                    id: "15",
                    src: "hda"
                }
            ]
        }
    ]
};

// ============================================================================
export default {
    _1: datasets1,
    _1requestJSON: datasets1CreateRequestJSON
};
