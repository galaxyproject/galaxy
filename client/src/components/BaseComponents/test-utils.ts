import { createMemoryHistory, createRouter } from "vue-router";

const RouteStub = { render: () => null };

/**
 * A router with in-memory history for link components, matching each of `paths` and
 * served under `base` when given, so tests can check resolved hrefs and navigation
 * without touching `window.location`.
 */
export function createMemoryRouter({ paths = ["/", "/pages/create"], base }: { paths?: string[]; base?: string } = {}) {
    return createRouter({
        history: createMemoryHistory(base),
        routes: paths.map((path) => ({ path, component: RouteStub })),
    });
}
