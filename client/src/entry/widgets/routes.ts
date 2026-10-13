import { h } from "vue";
import type { LocationQueryValue, RouteRecordRaw } from "vue-router";

import GAlert from "@/components/BaseComponents/GAlert.vue";

/** Galaxy's encoded ids, so an analysis path such as `/histories/view` is never read as one. */
const ID = "[0-9a-f]+";

/** A query parameter given once and not empty, else undefined. */
function single(value: LocationQueryValue | LocationQueryValue[] | undefined) {
    return typeof value === "string" && value ? value : undefined;
}

/**
 * The routes of the widgets app, relative to `/widgets/`. Each route serves a widget listed by
 * `/api/widgets` under its id, and is bounded to its resource.
 */
export const widgetRoutes: RouteRecordRaw[] = [
    {
        name: "history_graph",
        path: `/histories/:history_id(${ID})/graph`,
        component: () => import("./HistoryGraph.vue"),
        props: (route) => ({
            historyId: route.params.history_id,
            seedSrc: single(route.query.seed_src),
            seedId: single(route.query.seed_id),
        }),
    },
    {
        path: "/:pathMatch(.*)*",
        component: { render: () => h(GAlert, { variant: "danger", show: true }, () => "This view does not exist.") },
    },
];
