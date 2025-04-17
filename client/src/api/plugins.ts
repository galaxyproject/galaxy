import axios from "axios";

import { withPrefix } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

export interface Dataset {
    id: string;
    name: string;
}

export interface Plugin {
    description: string;
    href: string;
    html: string;
    logo?: string;
    name: string;
    target?: string;
}

export interface PluginData {
    hdas: Array<Dataset>;
}

export async function fetchPlugins(): Promise<Array<Plugin>> {
    try {
        const { data } = await axios.get(withPrefix(`/api/plugins`));
        return data;
    } catch (error) {
        rethrowSimple(error);
    }
}

export async function fetchPlugin(id: string): Promise<Array<Plugin>> {
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
