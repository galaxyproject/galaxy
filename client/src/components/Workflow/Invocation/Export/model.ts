import { type IconDefinition } from "@fortawesome/fontawesome-svg-core";

import { type ExportParams } from "@/components/Common/models/exportRecordModel";
/**
 * Defines a UI plugin that can export a workflow invocation to a particular format.
 */
export interface InvocationExportPlugin {
    /** The unique identifier for the plugin. */
    id: string;
    /** The title of the plugin. */
    title: string;
    /** A markdown description of the plugin. */
    markdownDescription: string;
    /** The parameters to use when exporting the invocation. */
    exportParams: ExportParams;
    /** Any additional actions that can be taken in addition to the main export action. */
    additionalActions: InvocationExportPluginAction[];
}

/**
 * Defines an action that can be taken in addition to the main export action.
 */
export interface InvocationExportPluginAction {
    /** The unique identifier for the action. */
    id: string;
    /** The title of the action. */
    title: string;
    /** The icon to display in the button for the action. */
    icon?: IconDefinition | string;
    /** The function to run when the action is triggered.
     * @param modal - The modal dialog to show when the action is run.
     */
    run: (modal: any) => void;
    /** The Vue component to render in a modal dialog when the action is run. */
    modal?: any;
}
