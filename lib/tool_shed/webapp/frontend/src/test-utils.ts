import { createMemoryHistory, createRouter } from "vue-router"

/**
 * A router with in-memory history where every path matches, so RouterLinks
 * resolve without touching `window.location`.
 */
export function createMemoryRouter() {
    return createRouter({
        history: createMemoryHistory(),
        routes: [{ path: "/:any(.*)*", component: { template: "<div />" } }],
    })
}
