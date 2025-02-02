import vegaBarChart from "./templates/vega-bar-chart.json"

export const cellTemplates = [
    {
        name: "Markdown",
        examples: [
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
        examples: [
            {
                title: "Bar Diagram",
                description: "Basic bar diagram",
                cell: {
                    name: "vega",
                    content: JSON.stringify(vegaBarChart, null, 4),
                },
            },
        ],
    },
];
