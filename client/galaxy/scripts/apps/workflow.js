import WorkflowView from "mvc/workflow/workflow-view";

export default function workflowApp(options) {
    new WorkflowView(options);
}

window.workflowApp = workflowApp;
