import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { type AdminExtension, useAdminExtensionsStore } from "./adminExtensionsStore";

const EXTENSIONS: AdminExtension[] = [
    {
        id: "anvil",
        section: "AnVIL",
        items: [
            { id: "monitor", type: "link", title: "Cluster Monitor", url: "/monitor", target: "iframe" },
            { id: "docs", type: "link", title: "Docs", url: "https://example.org", target: "new_tab" },
        ],
    },
];

const { server, http } = useServerMock();

describe("adminExtensionsStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("loads extensions from the server", async () => {
        server.use(
            http.get("/api/admin/extensions", ({ response }) => {
                return response(200).json(EXTENSIONS);
            }),
        );
        const store = useAdminExtensionsStore();
        expect(store.extensions).toEqual([]);
        expect(store.loaded).toBe(false);

        await store.loadExtensions();
        await flushPromises();

        expect(store.loaded).toBe(true);
        expect(store.errorMessage).toBeNull();
        expect(store.extensions).toEqual(EXTENSIONS);
    });

    it("resolves items by extension and item id", async () => {
        server.use(
            http.get("/api/admin/extensions", ({ response }) => {
                return response(200).json(EXTENSIONS);
            }),
        );
        const store = useAdminExtensionsStore();
        await store.loadExtensions();

        expect(store.getItem("anvil", "monitor")?.url).toBe("/monitor");
        expect(store.getItem("anvil", "missing")).toBeUndefined();
        expect(store.getItem("missing", "monitor")).toBeUndefined();
    });

    it("fetches only once across repeated calls", async () => {
        const handler = vi.fn(() => EXTENSIONS);
        server.use(
            http.get("/api/admin/extensions", ({ response }) => {
                return response(200).json(handler());
            }),
        );
        const store = useAdminExtensionsStore();
        await Promise.all([store.loadExtensions(), store.loadExtensions()]);
        await store.loadExtensions();

        expect(handler).toHaveBeenCalledTimes(1);
    });

    it("records an error message when the request fails", async () => {
        server.use(
            http.get("/api/admin/extensions", ({ response }) => {
                return response("5XX").json({ err_msg: "boom", err_code: 0 }, { status: 500 });
            }),
        );
        const store = useAdminExtensionsStore();
        await store.loadExtensions();

        expect(store.loaded).toBe(false);
        expect(store.extensions).toEqual([]);
        expect(store.errorMessage).toContain("boom");
    });
});
