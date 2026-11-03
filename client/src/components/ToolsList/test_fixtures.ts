import { getFakeTool, getFakeToolFormConfig } from "@tests/test-data/tools";
import { HttpResponse } from "msw";

import { http } from "@/api/client/__mocks__/http";
import { TOOLBOX_TOOLS } from "@/components/Panels/test_fixtures";

export const CATALOG_TOOLS = TOOLBOX_TOOLS.map((tool) => getFakeTool(tool));

/** Search the small catalog by its names or curated tags, returning IDs as Galaxy does. */
function catalogResults(query: string) {
    const tags = [...query.matchAll(/tool_tags:\((?:"([^"]+)"|([^)]*))\)/g)].map((match) =>
        (match[1] ?? match[2] ?? "").toLowerCase(),
    );
    if (tags.length) {
        const matchesTag = (tool: (typeof CATALOG_TOOLS)[number], tag: string) =>
            tool.tool_tags?.some((value) => value.toLowerCase() === tag) ?? false;
        return CATALOG_TOOLS.filter((tool) =>
            /\bOR\b/.test(query)
                ? tags.some((tag) => matchesTag(tool, tag))
                : tags.every((tag) => matchesTag(tool, tag)),
        ).map((tool) => tool.id);
    }
    const name = query.match(/name:\(([^)]*)\)/)?.[1] ?? query;
    return CATALOG_TOOLS.filter((tool) =>
        `${tool.name} ${tool.description}`.toLowerCase().includes(name.toLowerCase()),
    ).map((tool) => tool.id);
}

export const catalogHandlers = {
    tools: http.untyped.get("/api/tools", ({ request }) => {
        const query = new URL(request.url).searchParams.get("q");
        return HttpResponse.json(query ? catalogResults(query) : CATALOG_TOOLS);
    }),
    toolBuild: http.untyped.get("/api/tools/:tool_id/build", ({ params }) => {
        const tool = CATALOG_TOOLS.find((candidate) => candidate.id === String(params.tool_id));
        if (!tool) {
            return HttpResponse.json({ err_code: 400014, err_msg: "Tool not found." }, { status: 400 });
        }
        return HttpResponse.json({
            ...getFakeToolFormConfig(tool),
            help_format: "restructuredtext",
        });
    }),
};
