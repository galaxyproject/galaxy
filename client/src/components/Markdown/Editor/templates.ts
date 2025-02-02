import vegaBarChart from "./templates/vega-bar-chart.json";
import vegaLineChart from "./templates/vega-line-chart.json";
import type { TemplateCategory } from "./types";

export const cellTemplates: Array<TemplateCategory> = [
    {
        name: "Markdown",
        templates: [
            {
                title: "Heading 1",
                description: "Main headline",
                cell: {
                    name: "markdown",
                    content: "# Heading 1",
                },
            },
            {
                title: "Heading 2",
                description: "Section headline",
                cell: {
                    name: "markdown",
                    content: "## Heading 2",
                },
            },
            {
                title: "Heading 3",
                description: "Subhead",
                cell: {
                    name: "markdown",
                    content: "### Heading 3",
                },
            },
        ],
    },
    {
        name: "Galaxy",
        templates: [
            {
                title: "Collection",
                description: "Display a Collection",
                cell: {
                    name: "galaxy",
                    content: "history_dataset_collection_display(history_dataset_collection_id=)",
                },
            },
            {
                title: "Dataset",
                description: "Display a Dataset",
                cell: {
                    name: "galaxy",
                    content: "history_dataset_display(history_dataset_id=)",
                },
            },
            {
                title: "Dataset Details",
                description: "Display a Dataset Information",
                cell: {
                    name: "galaxy",
                    content: "history_dataset_info(history_dataset_id=)",
                },
            },
            {
                title: "Dataset Index",
                description: "Display a Dataset Index",
                cell: {
                    name: "galaxy",
                    content: "history_dataset_index(history_dataset_id=)",
                },
            },
            {
                title: "Dataset Type",
                description: "Display a Dataset Type",
                cell: {
                    name: "galaxy",
                    content: "history_dataset_index(history_dataset_type=)",
                },
            },
            {
                title: "Embedded Dataset",
                description: "Embed a Dataset",
                cell: {
                    name: "galaxy",
                    content: "history_dataset_embedded(history_dataset_id=)",
                },
            },
            {
                title: "Embedded Dataset as Table",
                description: "Embed a Dataset as Table",
                cell: {
                    name: "galaxy",
                    content: "history_dataset_as_table(history_dataset_id=)",
                },
            },
            {
                title: "Image",
                description: "Embed an Image",
                cell: {
                    name: "galaxy",
                    content: "history_dataset_as_image(history_dataset_id=)",
                },
            },
            {
                title: "Link to Dataset",
                description: "Create link to a Dataset",
                cell: {
                    name: "galaxy",
                    content: "history_dataset_link(history_dataset_id=)",
                },
            },
            {
                title: "Link to Import",
                description: "Link to Import a History",
                cell: {
                    name: "galaxy",
                    content: "history_link(history_id=)",
                },
            },
            {
                title: "Name of Dataset",
                description: "Display a Dataset name",
                cell: {
                    name: "galaxy",
                    content: "history_dataset_name(history_dataset_id=)",
                },
            },
            {
                title: "Peek into Dataset",
                description: "Display a Dataset peek",
                cell: {
                    name: "galaxy",
                    content: "history_dataset_peek(history_dataset_id=)",
                },
            },
            {
                title: "Job Metrics as Table",
                description: "Display job resource consumption",
                cell: {
                    name: "galaxy",
                    content: "job_metrics(job_id=)",
                },
            },
            {
                title: "Job Parameters as Table",
                description: "Display the input parameters of a Job",
                cell: {
                    name: "galaxy",
                    content: "job_parameters(job_id=)",
                },
            },
            {
                title: "Tool Error of Job run",
                description: "Display Tool errors",
                cell: {
                    name: "galaxy",
                    content: "tool_stderr(job_id=)",
                },
            },
            {
                title: "Tool Output of Job run",
                description: "Display Tool standard output",
                cell: {
                    name: "galaxy",
                    content: "tool_stdout(job_id=)",
                },
            },
            {
                title: "Display a Workflow",
                description: "Display all Workflow steps",
                cell: {
                    name: "galaxy",
                    content: "workflow_display(workflow_id=)",
                },
            },
            {
                title: "Time a Workflow was invoked",
                description: "Inovcation time of a Workflow run",
                cell: {
                    name: "galaxy",
                    content: "invocation_time(workflow_id=)",
                },
            },
            {
                title: "Workflow (as image)",
                description: "A static image of a Workflow",
                cell: {
                    name: "galaxy",
                    content: "workflow_image(workflow_id=)",
                },
            },
            {
                title: "Workflow License",
                description: "Usage license of a Workflow",
                cell: {
                    name: "galaxy",
                    content: "workflow_license(workflow_id=)",
                },
            },
        ],
    },
    {
        name: "Vega",
        templates: [
            {
                title: "Bar Diagram",
                description: "Basic bar diagram",
                cell: {
                    name: "vega",
                    content: JSON.stringify(vegaBarChart, null, 4),
                },
            },
            {
                title: "Line Chart",
                description: "Basic line chart",
                cell: {
                    name: "vega",
                    content: JSON.stringify(vegaLineChart, null, 4),
                },
            },
        ],
    },
];
