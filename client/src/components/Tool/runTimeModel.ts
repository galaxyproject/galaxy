import { schemaToInterface } from "schema-to-ts";
import { parse } from "yaml";

import { GalaxyApi } from "@/api";

async function fetchRuntimeSchema(toolSource: any) {
    const { data, error } = await GalaxyApi().POST("/api/unprivileged_tools/runtime_model", {
        body: {
            active: true,
            allow_load: false,
            hidden: false,
            representation: toolSource,
            src: "representation",
        },
    });
    return { data, error };
}

export async function fetchAndConvertSchemaToInterface(yamlString: string) {
    let toolSource = {};
    try {
        toolSource = parse(yamlString);
    } catch {
        return "";
    }
    const { data, error } = await fetchRuntimeSchema(toolSource);
    if (error) {
        console.log(error);
        return "";
    }
    const contents = await schemaToInterface(data as any);
    return contents;
}
