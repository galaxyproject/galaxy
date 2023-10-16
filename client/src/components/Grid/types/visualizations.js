export const VisualizationsGrid = {
    url: "/api/visualizations?view=detailed&sharing=true",
    resource: "visualizations",
    item: "visualization",
    plural: "Visualizations",
    title: "Visualizations",
    fields: [
        {
            title: "title",
            operations: [
                {
                    title: "Edit Attributes",
                    handler: (data, router) => {
                        router.push(`/visualizations/edit?id=${data.id}`);
                    },
                },
                {
                    title: "Share and Publish",
                    handler: (data, router) => {
                        router.push(`/visualizations/sharing?id=${data.id}`);
                    },
                },
                {
                    title: "Delete",
                    handler: (data) => {
                        return `'${data.title}' has been deleted.`;
                    },
                },
            ],
        },
        {
            key: "type",
            type: "string",
        },
        {
            key: "create_time",
            type: "date",
        },
        {
            key: "update_time",
            type: "date",
        },
        {
            key: "sharing",
            type: "sharing",
        },
        {
            key: "username_and_slug",
            type: "link",
        },
        {
            key: "tags",
            type: "string",
        },
    ],
};
