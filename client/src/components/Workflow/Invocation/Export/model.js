/**
 * Defines a UI plugin that can export a workflow invocation to a particular format.
 */
export class InvocationExportPlugin {
    constructor(props = {}) {
        /**
         * The unique ID for this plugin.
         * @type {string}
         */
        this.id = props.id ?? "undefined-plugin";

        /**
         * The display title for this plugin.
         * @type {string}
         */
        this.title = props.title ?? "Unknown Plugin";

        /**
         * A detailed description of the format in Markdown.
         * @type {string}
         */
        this.markdownDescription = props.markdownDescription ?? "No description provided";

        /**
         * An object with parameters for the Galaxy export store that handles the download format in the backend.
         * Check lib/galaxy/model/store/__init__.py::get_export_store_factory for more info.
         * @type {Object}
         */
        this.exportParams = props.exportParams ?? null;

        /**
         * A list of additional actions that this plugin can do with the exported invocation in addition
         * to direct downloading the exported file or exporting it to a remote file source.
         * @type {InvocationExportPluginAction[]}
         */
        this.additionalActions = props.additionalActions ?? [];
    }
}

export class InvocationExportPluginAction {
    constructor(props = {}) {
        /**
         * The unique ID for this action.
         * @type {string}
         */
        this.id = props.id ?? "undefined-action";

        /**
         * The display title of the button for this action.
         * @type {string}
         */
        this.title = props.title ?? "Untitled action";

        /** An optional (fontawesome) icon definition for the action button. */
        this.icon = props.icon ?? null;

        /**
         * The function that will run when the action button is pressed.
         * @type {function}
         */
        this.run =
            props.run ??
            (() => {
                alert("Undefined 'run' function in InvocationExportPluginAction");
            });

        /**
         * The optional modal dialog (component) that can be displayed when running this action.
         * @type {string}
         */
        this.modal = props.modal ?? null;
    }
}
