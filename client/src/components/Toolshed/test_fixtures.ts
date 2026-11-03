import { HttpResponse } from "msw";

import { http } from "@/api/client/__mocks__/http";
import type { components } from "@/api/schema";

export type InstalledRepository = components["schemas"]["InstalledToolShedRepository"];

/** The `tool_shed_urls` config of a Galaxy that installs from the main and test Tool Sheds. */
export const TOOL_SHED_URLS = ["https://toolshed.g2.bx.psu.edu/", "https://testtoolshed.g2.bx.psu.edu/"];

type Repository = Pick<InstalledRepository, "id" | "name" | "owner" | "tool_shed" | "changeset_revision">;

/** An installed repository as `/api/tool_shed_repositories` lists it, up to date unless `newerVersion`. */
function installedRepository(repository: Repository, { newerVersion = false } = {}): InstalledRepository {
    return {
        model_class: "ToolShedRepository",
        status: "Installed",
        deleted: false,
        ctx_rev: "12",
        error_message: "",
        installed_changeset_revision: repository.changeset_revision,
        dist_to_shed: false,
        uninstalled: false,
        // The Tool Shed reports these flags as strings.
        tool_shed_status: {
            latest_installable_revision: newerVersion ? "False" : "True",
            revision_update: "False",
            revision_upgrade: newerVersion ? "True" : "False",
            repository_deprecated: "False",
        },
        ...repository,
    };
}

/** Installed from the main Tool Shed, which has a newer version. */
export const BOWTIE2 = installedRepository(
    {
        id: "f2db41e1fa331b3e",
        name: "bowtie2",
        owner: "devteam",
        tool_shed: "toolshed.g2.bx.psu.edu",
        changeset_revision: "d5ceb9f3c25b",
    },
    { newerVersion: true },
);
/** Installed from the main Tool Shed, up to date. */
export const FASTQC = installedRepository({
    id: "1cd8e2f6b131e891",
    name: "fastqc",
    owner: "devteam",
    tool_shed: "toolshed.g2.bx.psu.edu",
    changeset_revision: "5ec9f6bceaee",
});
/** Installed from the test Tool Shed, up to date. */
export const FASTP = installedRepository({
    id: "a799d38679e985db",
    name: "fastp",
    owner: "iuc",
    tool_shed: "testtoolshed.g2.bx.psu.edu",
    changeset_revision: "dbf9c561ef29",
});

/** Tool Shed's Category response model (tool_shed_client/schema/__init__.py). */
export interface ToolShedCategory {
    id: string;
    name: string;
    description: string;
    deleted: boolean;
    repositories: number;
}

export const TOOL_SHED_CATEGORIES: ToolShedCategory[] = [
    {
        id: "f2db41e1fa331b3e",
        name: "Sequence Analysis",
        description: "Tools for analysing biological sequences",
        deleted: false,
        repositories: 18,
    },
    {
        id: "1cd8e2f6b131e891",
        name: "Visualization",
        description: "Tools for plotting and visualising data",
        deleted: false,
        repositories: 7,
    },
];

/** Galaxy's admin proxy forwards the registered Tool Shed's category JSON unchanged. */
export function toolShedCategories(
    categories: ToolShedCategory[] = TOOL_SHED_CATEGORIES,
    beforeResponse?: () => Promise<void>,
) {
    return http.untyped.get("/api/tool_shed/request", async ({ request }) => {
        const query = new URL(request.url).searchParams;
        if (query.get("controller") === "categories" && query.get("tool_shed_url") === TOOL_SHED_URLS[0]) {
            // Capture a pending mount's promise here, before awaiting it.
            await beforeResponse?.();
            return HttpResponse.json(categories);
        }
    });
}
