import STATES from "mvc/dataset/states";
// ============================================================================
// plain 3 step job chain
var datasets1 = [
    { name: "SET1-01_1.fastq", state: STATES.OK, id: "011" },
    { name: "SET1-01_2.fastq", state: STATES.OK, id: "012" },
    { name: "SET1-02_1.fastq", state: STATES.OK, id: "021" },
    { name: "SET1-02_2.fastq", state: STATES.OK, id: "022" },
    { name: "SET1-03_1.fastq", state: STATES.OK, id: "031" },
    { name: "SET1-03_2.fastq", state: STATES.OK, id: "032" },
    { name: "SET1-04_1.fastq", state: STATES.OK, id: "041" },
    { name: "SET1-04_2.fastq", state: STATES.OK, id: "042" },
    { name: "SET1-05_1.fastq", state: STATES.OK, id: "051" },
    { name: "SET1-05_2.fastq", state: STATES.OK, id: "052" },
    { name: "SET1-06_1.fastq", state: STATES.OK, id: "061" },
    { name: "SET1-06_2.fastq", state: STATES.OK, id: "062" },
    { name: "SET1-07_1.fastq", state: STATES.OK, id: "071" },
    { name: "SET1-07_2.fastq", state: STATES.OK, id: "072" },
];

var datasets2 = [
    { name: "DP134_1_FS_PSII_FSB_42C_A10.1.fastq", state: STATES.OK, id: "101" },
    { name: "DP134_1_FS_PSII_FSB_42C_A10.2.fastq", state: STATES.OK, id: "102" },
];

var datasets3 = [
    { name: "UII_moo_1.1.fastq", state: STATES.OK, id: "11" },
    { name: "UII_moo_1.2.fastq", state: STATES.OK, id: "12" },
];

var datasets4 = [
    { name: "SET1-01_R1.fastq", state: STATES.OK, id: "111" },
    { name: "SET1-01_R2.fastq", state: STATES.OK, id: "112" },
    { name: "SET1-02_R1.fastq", state: STATES.OK, id: "211" },
    { name: "SET1-02_R2.fastq", state: STATES.OK, id: "212" },
    { name: "SET1-03_R1.fastq", state: STATES.OK, id: "311" },
    { name: "SET1-03_R2.fastq", state: STATES.OK, id: "312" },
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
    _4: datasets4,
};
