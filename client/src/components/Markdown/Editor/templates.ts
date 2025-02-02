import vegaBarChart from "./templates/vega-bar-chart.json";
import vegaLineChart from "./templates/vega-line-chart.json";
import type { CellType } from "./types";

interface TemplateEntry {
    title: string;
    description: string;
    cell: CellType;
}

interface TemplateCategory {
    name: string;
    templates: Array<TemplateEntry>;
}

export const templateCategories: Array<TemplateCategory> = [
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

export function getTemplates(query: string): Array<TemplateCategory> {
    const filteredCategories: Array<TemplateCategory> = [];
    templateCategories.forEach((category) => {
        const matchedTemplates = category.templates.filter(
            (template) =>
                category.name.toLowerCase().includes(query.toLowerCase()) ||
                template.title.toLowerCase().includes(query.toLowerCase()) ||
                template.description.toLowerCase().includes(query.toLowerCase())
        );
        if (matchedTemplates.length > 0) {
            filteredCategories.push({
                name: category.name,
                templates: matchedTemplates,
            });
        }
    });

    return filteredCategories;
}
