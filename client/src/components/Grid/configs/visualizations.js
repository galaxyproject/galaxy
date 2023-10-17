export const VisualizationsGrid = {
    url: "/api/visualizations?view=detailed&sharing=true",
    resource: "visualizations",
    item: "visualization",
    plural: "Visualizations",
    title: "Saved Visualizations",
    fields: [
        {
            title: "title",
            operations: [
                {
                    title: "Open",
                    handler: (data, router) => {
                        router.push(`/visualizations/edit?id=${data.id}`);
                    },
                },
                {
                    title: "Edit Attributes",
                    handler: (data, router) => {
                        router.push(`/visualizations/edit?id=${data.id}`);
                    },
                },
                {
                    title: "Copy",
                    handler: (data) => {
                        return {
                            status: "success",
                            message: `'${data.title}' has been deleted.`,
                        };
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
                        return {
                            status: "success",
                            message: `'${data.title}' has been deleted.`,
                        };
                    },
                },
            ],
        },
        {
            key: "type",
            title: "Type",
            type: "string",
        },
        {
            key: "sharing",
            title: "Sharing",
            type: "sharing",
        },
        {
            key: "tags",
            title: "Tags",
            type: "tags",
            handler: async (data) => {
                alert(data.tags);
            },
        },
        {
            key: "create_time",
            title: "Created",
            type: "date",
        },
        {
            key: "update_time",
            title: "Last updated",
            type: "date",
        },
    ],
};
