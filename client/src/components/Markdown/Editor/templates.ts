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
