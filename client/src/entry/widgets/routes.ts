import { h } from "vue";
import type { LocationQuery, LocationQueryValue, RouteRecordRaw } from "vue-router";

import { pageProps, workflowProps } from "@/router/publishedProps";

import GAlert from "@/components/BaseComponents/GAlert.vue";

/** Galaxy's encoded ids, so an analysis path such as `/histories/view` is never read as one. */
const ID = "[0-9a-f]+";

/** A query parameter given once and not empty, else undefined. */
function single(value: LocationQueryValue | LocationQueryValue[] | undefined) {
    return typeof value === "string" && value ? value : undefined;
}

function singleValues(query: LocationQuery) {
    const result: Record<string, string> = {};
    for (const [name, value] of Object.entries(query)) {
        const text = single(value);
        if (text) {
            result[name] = text;
        }
    }
    return result;
}

/**
 * The routes of the widgets app, under `/widgets/`. Each route serves a widget listed by
 * `/api/widgets` under its id, and is bounded to its resource.
 */
export const widgetRoutes: RouteRecordRaw[] = [
    {
        name: "history_graph",
        path: `/widgets/histories/:history_id(${ID})/graph`,
        component: () => import("./HistoryGraph.vue"),
        props: (route) => {
            const query = singleValues(route.query);
            return { historyId: route.params.history_id, seedSrc: query.seed_src, seedId: query.seed_id };
        },
    },
    {
        name: "page",
        path: `/widgets/pages/:page_id(${ID})`,
        component: () => import("@/components/Page/PageView.vue"),
        props: (route) => ({ ...pageProps(route.params.page_id, singleValues(route.query)), embed: true }),
    },
    {
        name: "workflow",
        path: `/widgets/workflows/:workflow_id(${ID})`,
        component: () => import("@/components/Workflow/Published/WorkflowPublished.vue"),
        props: (route) => {
            const query = singleValues(route.query);
            return {
                ...workflowProps(route.params.workflow_id, query),
                version: /^\d+$/.test(query.version ?? "") ? Number(query.version) : undefined,
                embed: true,
            };
        },
    },
    {
        path: "/:pathMatch(.*)*",
        component: { render: () => h(GAlert, { variant: "danger", show: true }, () => "This view does not exist.") },
    },
];
