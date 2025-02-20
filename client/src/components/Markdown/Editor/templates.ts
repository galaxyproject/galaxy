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
                    configure: true,
                    content: "history_dataset_collection_display()",
                },
            },
            {
                title: "Dataset",
                description: "Display a Dataset",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "history_dataset_display()",
                },
            },
            {
                title: "Dataset Details",
                description: "Display a Dataset Information",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "history_dataset_info()",
                },
            },
            {
                title: "Dataset Index",
                description: "Display a Dataset Index",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "history_dataset_index()",
                },
            },
            {
                title: "Dataset Type",
                description: "Display a Dataset Type",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "history_dataset_index()",
                },
            },
            {
                title: "Embedded Dataset",
                description: "Embed a Dataset",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "history_dataset_embedded()",
                },
            },
            {
                title: "Embedded Dataset as Table",
                description: "Embed a Dataset as Table",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "history_dataset_as_table()",
                },
            },
            {
                title: "Image",
                description: "Embed an Image",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "history_dataset_as_image()",
                },
            },
            {
                title: "Link to Dataset",
                description: "Create link to a Dataset",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "history_dataset_link()",
                },
            },
            {
                title: "Link to Import",
                description: "Link to Import a History",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "history_link()",
                },
            },
            {
                title: "Name of Dataset",
                description: "Display a Dataset name",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "history_dataset_name()",
                },
            },
            {
                title: "Peek into Dataset",
                description: "Display a Dataset peek",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "history_dataset_peek()",
                },
            },
            {
                title: "Job Metrics as Table",
                description: "Display job resource consumption",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "job_metrics()",
                },
            },
            {
                title: "Job Parameters as Table",
                description: "Display the input parameters of a Job",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "job_parameters()",
                },
            },
            {
                title: "Tool Error of Job run",
                description: "Display Tool errors",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "tool_stderr()",
                },
            },
            {
                title: "Tool Output of Job run",
                description: "Display Tool standard output",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "tool_stdout()",
                },
            },
            {
                title: "Display a Workflow",
                description: "Display all Workflow steps",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "workflow_display()",
                },
            },
            {
                title: "Time a Workflow was invoked",
                description: "Inovcation time of a Workflow run",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "invocation_time()",
                },
            },
            {
                title: "Workflow (as image)",
                description: "A static image of a Workflow",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "workflow_image()",
                },
            },
            {
                title: "Workflow License",
                description: "Usage license of a Workflow",
                cell: {
                    name: "galaxy",
                    configure: true,
                    content: "workflow_license()",
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
