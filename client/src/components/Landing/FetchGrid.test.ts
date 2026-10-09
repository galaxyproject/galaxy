import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { AnyFetchTarget } from "@/api/tools";

import FetchGrid from "./FetchGrid.vue";

const localVue = getLocalVue(true);

const { server, http } = useServerMock();
beforeEach(() => {
    server.use(
        http.get("/api/configuration", ({ response }) => response(200).json({})),
        http.get("/api/genomes", ({ response }) => response(200).json([])),
        http.get("/api/datatypes", ({ response }) => response(200).json([])),
    );
});

function urlTarget(url: string): AnyFetchTarget {
    return {
        destination: { type: "hdas" },
        elements: [{ src: "url", url, ext: "txt" }],
    } as unknown as AnyFetchTarget;
}

describe("FetchGrid", () => {
    it("shows the rows of each new target", async () => {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);
        const wrapper = mount(FetchGrid, {
            props: { target: urlTarget("http://example.com/a.txt") },
            global: withPlugins(localVue, pinia),
            attachTo: document.body,
        });
        await flushPromises();
        expect(wrapper.text()).toContain("http://example.com/a.txt");

        for (const url of ["http://example.com/b.txt", "http://example.com/c.txt"]) {
            await wrapper.setProps({ target: urlTarget(url) });
            await flushPromises();
            expect(wrapper.text()).toContain(url);
        }
        wrapper.unmount();
    });
});
