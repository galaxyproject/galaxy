import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";
import { rethrowSimple } from "utils/simple-error";

async function toolSource({ id }) {
    const url = `${getAppRoot()}api/tools/${id}/raw_tool_source`;
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export const ToolSourceProvider = SingleQueryProvider(toolSource);
