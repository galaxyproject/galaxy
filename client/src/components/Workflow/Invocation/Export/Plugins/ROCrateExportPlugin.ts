import { type InvocationExportPlugin } from "@/components/Workflow/Invocation/Export/Plugins";

export const RO_CRATE_EXPORT_PLUGIN: InvocationExportPlugin = {
    id: "ro-crate",
    title: "Research Object Crate",
    img: "https://www.researchobject.org/workflow-run-crate/img/ro-crate-workflow-run.svg",
    url: "https://www.researchobject.org/ro-crate/",
    markdownDescription: `
RO-Crate is a community effort to establish a lightweight approach to packaging research data with their metadata. It is based on schema.org annotations in JSON-LD, and aims to make best-practice in formal metadata description accessible and practical for use in a wider variety of situations, from an individual researcher working with a folder of data, to large data-intensive computational research environments.

Learn more about [RO Crate](https://www.researchobject.org/ro-crate/).`,
    exportParams: {
        modelStoreFormat: "rocrate.zip",
        includeFiles: true,
        includeDeleted: false,
        includeHidden: false,
    },
};
