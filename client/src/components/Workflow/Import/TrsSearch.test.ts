import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import TrsSearch from "./TrsSearch.vue";

const { server, http } = useServerMock();

const TRS_SERVERS = [
    { id: "dockstore", label: "dockstore", link_url: "https://dockstore.org", doc: "Dockstore" },
    { id: "workflowhub", label: "workflowhub", link_url: "https://workflowhub.eu", doc: "WorkflowHub" },
];
const QUERY = "organization: iwc-workflows";
// longer than the 500 ms debounce of the search input
const DEBOUNCE_WAIT = 600;

function wait(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function mountTrsSearch() {
    return mount(TrsSearch as object, { global: getLocalVue(true) });
}

describe("TrsSearch", () => {
    it("encodes the query and server in the search URL", async () => {
        const searches: Record<string, string>[] = [];
        server.use(
            http.untyped.get("/api/trs_consume/servers", () => HttpResponse.json(TRS_SERVERS)),
            http.untyped.get("/api/trs_search", ({ request }) => {
                searches.push(Object.fromEntries(new URL(request.url).searchParams));
                return HttpResponse.json([]);
            }),
        );

        const wrapper = mountTrsSearch();
        await flushPromises();

        const input = wrapper.find("#trs-search-query");
        await input.setValue("rna-seq & qc #1 + more");
        await input.trigger("change");
        await flushPromises();

        expect(searches).toEqual([{ query: "rna-seq & qc #1 + more", trs_server: "dockstore" }]);
    });

    it("keeps a query typed before the TRS server list loads and searches it on that server", async () => {
        let resolveServers: () => void = () => {};
        const serversLoaded = new Promise<void>((resolve) => {
            resolveServers = resolve;
        });
        const searches: { query: string | null; trsServer: string | null }[] = [];
        server.use(
            http.untyped.get("/api/trs_consume/servers", async () => {
                await serversLoaded;
                return HttpResponse.json(TRS_SERVERS);
            }),
            http.untyped.get("/api/trs_search", ({ request }) => {
                const params = new URL(request.url).searchParams;
                searches.push({ query: params.get("query"), trsServer: params.get("trs_server") });
                return HttpResponse.json([]);
            }),
        );

        const wrapper = mountTrsSearch();
        const input = wrapper.find("#trs-search-query");
        await input.setValue(QUERY);
        await wait(DEBOUNCE_WAIT);
        await flushPromises();

        // no server is selected yet, so there is nothing to search
        expect(searches).toEqual([]);

        resolveServers();
        await wait(50);
        await flushPromises();

        expect((input.element as HTMLInputElement).value).toBe(QUERY);
        expect(searches).toEqual([{ query: QUERY, trsServer: "dockstore" }]);
    });

    it("clears the query when switching to another TRS server", async () => {
        server.use(
            http.untyped.get("/api/trs_consume/servers", () => HttpResponse.json(TRS_SERVERS)),
            http.untyped.get("/api/trs_search", () => HttpResponse.json([])),
        );

        const wrapper = mountTrsSearch();
        await flushPromises();
        const input = wrapper.find("#trs-search-query");
        await input.setValue(QUERY);
        await wait(DEBOUNCE_WAIT);
        await flushPromises();
        expect((input.element as HTMLInputElement).value).toBe(QUERY);

        const workflowhub = wrapper.findAll(".dropdown-item").filter((item) => item.text() === "workflowhub");
        await workflowhub[0]!.trigger("click");
        await flushPromises();

        expect((input.element as HTMLInputElement).value).toBe("");
    });
});
