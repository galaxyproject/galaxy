import axios from "axios";

import { withPrefix } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

export interface Dataset {
    id: string;
    name: string;
}

export interface Plugin {
    description: string;
    ext?: Array<string>;
    help?: string;
    href: string;
    html: string;
    logo?: string;
    name: string;
    target?: string;
    tags?: Array<string>;
    tests?: Array<any>;
}

export interface PluginData {
    hdas: Array<Dataset>;
}

export async function fetchPlugins(datasetId?: string): Promise<Array<Plugin>> {
    try {
        const query = datasetId ? `?dataset_id=${datasetId}` : "";
        const { data } = await axios.get(withPrefix(`/api/plugins${query}`));
        return data;
    } catch (error) {
        rethrowSimple(error);
    }
}

export async function fetchPlugin(id: string): Promise<Plugin> {
    try {
        const { data } = await axios.get(withPrefix(`/api/plugins/${id}`));
        return data;
    } catch (error) {
        rethrowSimple(error);
    }
}

export async function fetchPluginHistoryItems(id: string, history_id: string): Promise<PluginData> {
    try {
        const { data } = await axios.get(`/api/plugins/${id}?history_id=${history_id}`);
        return data;
    } catch (error) {
        rethrowSimple(error);
    }
}
