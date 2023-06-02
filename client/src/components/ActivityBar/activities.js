/**
 * Contains build in activities
 */

export const Activities = [
    {
        id: "upload",
    },
    {
        id: "tools",
    },
    {
        id: "workflow",
    },
    {
        id: "visualizations",
        title: "Visualize",
        description: "Shows to the list of available visualizations.",
        icon: "chart-bar",
        tooltip: "Visualize datasets",
        to: "/visualizations",
        optional: true,
    },
    {
        id: "histories",
        title: "Histories",
        description: "Shows all of your histories in the center panel.",
        icon: "fa-hdd",
        tooltip: "Show all histories",
        to: "/histories/list",
        optional: true,
    },
    {
        id: "datasets",
        title: "Datasets",
        description: "Displays all of your datasets across all histories in the center panel.",
        icon: "fa-folder",
        tooltip: "Show all datasets",
        to: "/datasets/list",
        optional: true,
    },
    {
        id: "invocation",
        title: "Invocations",
        description: "Displays all workflow invocations.",
        icon: "fa-list",
        tooltip: "Show all invocations",
        to: "/workflows/invocations",
        optional: true,
    },
];

export default Activities;
