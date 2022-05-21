import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";
import { rethrowSimple } from "utils/simple-error";
import beautify from "xml-beautifier";

async function toolSource({ id }) {
    const url = `${getAppRoot()}api/tools/${id}/raw_tool_source`;
    try {
        const { data, headers } = await axios.get(url);
        const result = {};
        result.language = headers.language;
        if (headers.language === "xml") {
            result.source = beautify(data);
        } else {
            result.source = data;
        }
        return result;
    } catch (e) {
        rethrowSimple(e);
    }
}

export const ToolSourceProvider = SingleQueryProvider(toolSource);
