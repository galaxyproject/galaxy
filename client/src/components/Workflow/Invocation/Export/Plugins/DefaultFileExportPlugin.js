import { InvocationExportPlugin } from "../model";

export const DEFAULT_FILE_EXPORT_PLUGIN = new InvocationExportPlugin({
    title: "File",
    markdownDescription: `Export the invocation to a compressed File containing the invocation data in Galaxy native format.`,
    exportParams: {
        modelStoreFormat: "tgz",
        includeFiles: false,
        includeDeleted: false,
        includeHidden: false,
    },
    additionalActions: [],
});
