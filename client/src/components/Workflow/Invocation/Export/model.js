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

export class InvocationExportPluginAction {
    constructor(props = {}) {
        this.id = props.id ?? "undefined-action";
        this.title = props.title ?? "Untitled action";
        this.icon = props.icon ?? null;
        this.run =
            props.run ??
            (() => {
                alert("Undefined 'run' function in InvocationExportPluginAction");
            });
        this.modal = props.modal ?? null;
    }
}
