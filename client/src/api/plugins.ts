import axios from "axios";

import { withPrefix } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

export interface Plugin {
    description: string;
    href: string;
    html: string;
    logo?: string;
    name: string;
    target?: string;
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
