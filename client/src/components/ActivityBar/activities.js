/**
 * Contains build in activities
 */

export const Activities = [
    {
        id: "invocation",
        title: "Invocations",
        description: "Access the workflow panel to search and execute workflows",
        icon: "fa-play",
        to: "/workflows/invocations",
        optional: true,
    },
    {
        id: "tools",
        title: "Tools",
        description: "Access the workflow panel to search and execute workflows",
        icon: "fa-wrench",
    },
    {
        id: "upload",
        title: "Upload",
        description: "Allows users to upload data and observe progress",
        icon: "fa-upload",
    },
    {
        id: "visualizations",
        title: "Visualize",
        description: "Visualize datasets",
        icon: "chart-bar",
        tooltip: "Visualize datasets",
        to: "/visualizations",
        optional: true,
    },
    {
        id: "histories",
        title: "Histories",
        description: "Visualize datasets",
        icon: "chart-bar",
        tooltip: "Visualize datasets",
        to: "/histories/list",
        optional: true,
    },
    {
        id: "histories",
        title: "Datasets",
        description: "All my datasets",
        icon: "wrench",
        tooltip: "Visualize datasets",
        to: "/datasets/list",
        optional: true,
    },
    {
        id: "workflow",
        title: "Workflow",
        description: "Access the workflow panel to search and execute workflows",
        icon: "fa-sitemap",
        optional: true,
    },
];

export default Activities;
