import STATES from "mvc/dataset/states";
// ============================================================================
// plain 3 step job chain
var datasets1 = [
    { name: "SET1-01_1.fastq", state: STATES.OK },
    { name: "SET1-01_2.fastq", state: STATES.OK },
    { name: "SET1-02_1.fastq", state: STATES.OK },
    { name: "SET1-02_2.fastq", state: STATES.OK },
    { name: "SET1-03_1.fastq", state: STATES.OK },
    { name: "SET1-03_2.fastq", state: STATES.OK },
    { name: "SET1-04_1.fastq", state: STATES.OK },
    { name: "SET1-04_2.fastq", state: STATES.OK },
    { name: "SET1-05_1.fastq", state: STATES.OK },
    { name: "SET1-05_2.fastq", state: STATES.OK },
    { name: "SET1-06_1.fastq", state: STATES.OK },
    { name: "SET1-06_2.fastq", state: STATES.OK },
    { name: "SET1-07_1.fastq", state: STATES.OK },
    { name: "SET1-07_2.fastq", state: STATES.OK },
];

var datasets2 = [
    { name: "DP134_1_FS_PSII_FSB_42C_A10.1.fastq", state: STATES.OK},
    { name: "DP134_1_FS_PSII_FSB_42C_A10.2.fastq", state: STATES.OK}
]

var datasets3 = [
    {name: "UII_moo_1.1.fastq", state: STATES.OK},
    {name: "UII_moo_1.2.fastq", state: STATES.OK}
]

var datasets4= [
    { name: "SET1-01_R1.fastq", state: STATES.OK },
    { name: "SET1-01_R2.fastq", state: STATES.OK },
    { name: "SET1-02_R1.fastq", state: STATES.OK },
    { name: "SET1-02_R2.fastq", state: STATES.OK },
    { name: "SET1-03_R1.fastq", state: STATES.OK },
    { name: "SET1-03_R2.fastq", state: STATES.OK },
]

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
                    src: "hda",
                },
                {
                    name: "reverse",
                    id: "3",
                    src: "hda",
                },
            ],
        },
        {
            collection_type: "paired",
            src: "new_collection",
            name: "SET1-06",
            element_identifiers: [
                {
                    name: "forward",
                    id: "4",
                    src: "hda",
                },
                {
                    name: "reverse",
                    id: "5",
                    src: "hda",
                },
            ],
        },
        {
            collection_type: "paired",
            src: "new_collection",
            name: "SET1-05",
            element_identifiers: [
                {
                    name: "forward",
                    id: "6",
                    src: "hda",
                },
                {
                    name: "reverse",
                    id: "7",
                    src: "hda",
                },
            ],
        },
        {
            collection_type: "paired",
            src: "new_collection",
            name: "SET1-04",
            element_identifiers: [
                {
                    name: "forward",
                    id: "8",
                    src: "hda",
                },
                {
                    name: "reverse",
                    id: "9",
                    src: "hda",
                },
            ],
        },
        {
            collection_type: "paired",
            src: "new_collection",
            name: "SET1-03",
            element_identifiers: [
                {
                    name: "forward",
                    id: "10",
                    src: "hda",
                },
                {
                    name: "reverse",
                    id: "11",
                    src: "hda",
                },
            ],
        },
        {
            collection_type: "paired",
            src: "new_collection",
            name: "SET1-02",
            element_identifiers: [
                {
                    name: "forward",
                    id: "12",
                    src: "hda",
                },
                {
                    name: "reverse",
                    id: "13",
                    src: "hda",
                },
            ],
        },
        {
            collection_type: "paired",
            src: "new_collection",
            name: "SET1-01",
            element_identifiers: [
                {
                    name: "forward",
                    id: "14",
                    src: "hda",
                },
                {
                    name: "reverse",
                    id: "15",
                    src: "hda",
                },
            ],
        },
    ],
};

// ============================================================================
export default {
    _1: datasets1,
    _1requestJSON: datasets1CreateRequestJSON,
    _2: datasets2,
    _3: datasets3,
    _4: datasets4
};
