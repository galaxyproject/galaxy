import { HttpResponse } from "msw";

import { http } from "@/api/client/__mocks__/http";
import type { useEntryPointStore } from "@/stores/entryPointStore";

type EntryPoint = ReturnType<typeof useEntryPointStore>["entryPoints"][number];

export const RUNNING_TOOLS: EntryPoint[] = [
    {
        model_class: "InteractiveToolEntryPoint",
        id: "52e496b945151ee8",
        job_id: "6fc9fbb81c497f69",
        name: "JupyterLab notebook",
        active: true,
        created_time: "2026-10-14T00:00:00",
        modified_time: "2026-10-14T00:00:10",
        output_datasets_ids: ["4e9e0c7225b0bb81"],
        target: "http://52e496b945151ee8.interactivetool.localhost:8080/lab",
    },
    {
        model_class: "InteractiveToolEntryPoint",
        id: "b887d74393f85b6d",
        job_id: "201592c8e20dac24",
        name: "RStudio workspace",
        active: true,
        created_time: "2026-10-14T00:05:00",
        modified_time: "2026-10-14T00:05:10",
        output_datasets_ids: ["ac59b4df0950f761"],
        target: "http://b887d74393f85b6d.interactivetool.localhost:8080/",
    },
];

/** The legacy controller is absent from OpenAPI; its serialized fields match entryPointStore. */
export function interactiveToolsHandlers(entries: EntryPoint[] = RUNNING_TOOLS) {
    return {
        entryPoints: http.untyped.get("/api/entry_points", ({ request }) => {
            const query = new URL(request.url).searchParams;
            if (query.get("running") !== "true" || query.has("job_id")) {
                throw new Error("Interactive tool list requires running=true without job_id.");
            }
            return HttpResponse.json(structuredClone(entries));
        }),
        // stop_entry_point returns None; the client removes the entry from its live store.
        stopEntryPoint: http.untyped.delete("/api/entry_points/:id", ({ params }) => {
            if (!entries.some((entry) => entry.id === params.id)) {
                throw new Error("Unexpected interactive tool entry point.");
            }
            return HttpResponse.json(null);
        }),
    };
}
