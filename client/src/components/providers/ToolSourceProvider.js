import axios from "axios";
import beautify from "xml-beautifier";
import { stringify } from "yaml";

import { SingleQueryProvider } from "@/components/providers/SingleQueryProvider";
import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

async function toolSource({ id, uuid }) {
    const url = `${getAppRoot()}api/tools/${uuid || id}/raw_tool_source`;
    try {
        const { data, headers } = await axios.get(url);
        const result = {};
        result.language = headers.language;
        if (headers.language === "xml") {
            result.source = beautify(data);
        } else if (headers.language == "yaml") {
            result.source = stringify(data);
        } else {
            result.source = data;
        }
        return result;
    } catch (e) {
        rethrowSimple(e);
    }
}

export const ToolSourceProvider = SingleQueryProvider(toolSource);
