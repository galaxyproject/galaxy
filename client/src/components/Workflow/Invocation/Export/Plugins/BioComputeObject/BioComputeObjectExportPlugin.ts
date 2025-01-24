import { type InvocationExportPlugin } from "@/components/Workflow/Invocation/Export/Plugins";

export const BIO_COMPUTE_OBJ_EXPORT_PLUGIN: InvocationExportPlugin = {
    id: "bco",
    title: "BioCompute Object",
    img: "https://www.biocomputeobject.org/static/media/logo.c8a91f1656efbad5d745.png",
    url: "https://biocomputeobject.org/",
    markdownDescription: `
A BioCompute Object (BCO) is the unofficial name for a JSON object that adheres to the [IEEE-2791-2020 standard](https://standards.ieee.org/ieee/2791/7337/).
A BCO is designed to communicate High-throughput Sequencing (HTS) analysis results, data set creation, data curation, and bioinformatics verification protocols.

Learn more about [BioCompute Objects](https://biocomputeobject.org/).

Instructions for [creating a BCO using Galaxy](https://w3id.org/biocompute/tutorials/galaxy_quick_start).`,
    exportParams: {
        modelStoreFormat: "bco.json",
        includeFiles: false,
        includeDeleted: false,
        includeHidden: false,
    },
};
