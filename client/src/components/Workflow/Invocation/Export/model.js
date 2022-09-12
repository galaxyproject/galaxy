/**
 * TODO
 */
export class InvocationExportPlugin {
    constructor(props = {}) {
        this.title = props.title || "Unknown Plugin";
        this.markdownDescription = props.markdownDescription || "No description provided";
        this.downloadFormat = props.downloadFormat || "zip";
        this.additionalActions = props.additionalActions || [];
    }
}
