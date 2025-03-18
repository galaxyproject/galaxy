import axios from "axios";

import { getAppRoot } from "@/onload";
import { rethrowSimple } from "@/utils/simple-error";

import type { TemplateEntry } from "./types";

export interface VisualizationType {
    description: string;
    html: string;
    logo?: string;
    name: string;
}

export async function getVisualizations(): Promise<Array<TemplateEntry>> {
    try {
        const { data } = await axios.get(`${getAppRoot()}api/plugins?embeddable=True`);
        return data.map((v: VisualizationType) => ({
            title: v.html,
            description: v.description || "",
            logo: v.logo ? `${getAppRoot()}${v.logo}` : undefined,
            cell: {
                name: "visualization",
                configure: true,
                content: `{ "visualization_name": "${v.name}", "visualization_title": "${v.html}" }`,
                // "dataset_url": "http://cdn.jsdelivr.net/gh/galaxyproject/galaxy-test-data/newick.nwk"
            },
        }));
    } catch (e) {
        rethrowSimple("Failed to load Visualizations.");
    }
}
