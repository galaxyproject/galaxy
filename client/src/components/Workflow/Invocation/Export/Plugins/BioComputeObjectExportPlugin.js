import { InvocationExportPlugin } from "../model";

export const BIO_COMPUTE_OBJ_EXPORT_PLUGIN = new InvocationExportPlugin({
    title: "BioCompute Object",
    markdownDescription: `
A BioCompute Object (BCO) is the unofficial name for a JSON object that adheres to the [IEEE-2791-2020 standard](https://standards.ieee.org/ieee/2791/7337/).
A BCO is designed to communicate High-throughput Sequencing (HTS) analysis results, data set creation, data curation, and bioinformatics verification protocols.

Learn more about [BioCompute Objects](https://biocomputeobject.org/).

Instructions for [creating a BCO using Galaxy](https://w3id.org/biocompute/tutorials/galaxy_quick_start).`,
    downloadFormat: "bco.zip",
    additionalActions: [
        // {
        //     title: "Send to BCODB",
        //     run: () => {},
        // },
    ],
});
