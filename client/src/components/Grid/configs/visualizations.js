import axios from "axios";

import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

export const VisualizationsGrid = {
    url: "/api/visualizations/detailed?sharing=true",
    resource: "visualizations",
    item: "visualization",
    plural: "Visualizations",
    title: "Saved Visualizations",
    fields: [
        {
            title: "Title",
            operations: [
                {
                    title: "Open",
                    handler: (data) => {
                        window.location = withPrefix(`/plugins/visualizations/${data.type}/saved?id=${data.id}`);
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
                    handler: async (data) => {
                        try {
                            const copyResponse = await axios.get(withPrefix(`/api/visualizations/${data.id}`));
                            const copyViz = copyResponse.data;
                            const newViz = {
                                title: `Copy of '${copyViz.title}'`,
                                type: copyViz.type,
                                config: copyViz.config,
                            };
                            await axios.post(withPrefix("/api/visualizations"), newViz);
                            return {
                                status: "success",
                                message: `'${data.title}' has been copied.`,
                            };
                        } catch (e) {
                            return {
                                status: "danger",
                                message: `Failed to copy '${data.title}': ${errorMessageAsString(e)}.`,
                            };
                        }
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
                    handler: async (data) => {
                        try {
                            await axios.put(withPrefix(`/api/visualizations/${data.id}`), { deleted: true });
                            return {
                                status: "success",
                                message: `'${data.title}' has been deleted.`,
                            };
                        } catch (e) {
                            return {
                                status: "danger",
                                message: `Failed to delete '${data.title}': ${errorMessageAsString(e)}.`,
                            };
                        }
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
            key: "tags",
            title: "Tags",
            type: "tags",
            handler: async (data) => {
                const tagPayload = {
                    item_id: data.id,
                    item_class: "Visualization",
                    item_tags: data.tags,
                };
                try {
                    await axios.put(withPrefix(`/api/tags`), tagPayload);
                } catch (e) {
                    rethrowSimple(e);
                }
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
        {
            key: "sharing",
            title: "Shared",
            type: "sharing",
        },
    ],
};
