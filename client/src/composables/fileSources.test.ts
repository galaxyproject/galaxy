import { createTestingPinia } from "@pinia/testing";
import { getFakeFileSource } from "@tests/test-data/fileSources";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent } from "vue";

import { useServerMock } from "@/api/client/__mocks__";

import { useFileSources } from "./fileSources";

const REMOTE_FILES_API_ROUTE = "/api/remote_files/plugins";

const TestComponent = defineComponent({
    setup() {
        return {
            ...useFileSources(),
        };
    },
    template: `
<div>
  <p>{{ isLoading }}</p>
  <p>{{ hasWritable }}</p>
  <p>{{ fileSources }}</p>
</div>
`,
});

enableAutoUnmount(afterEach);

function setupWrapper() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    return shallowMount(TestComponent, { global: withPlugins(getLocalVue(), pinia) });
}

const { server, http } = useServerMock();

describe("useFileSources", () => {
    beforeEach(() => {
        server.use(
            http.get(REMOTE_FILES_API_ROUTE, ({ response }) => {
                return response(200).json([]);
            }),
        );
    });

    it("is loading before the file-source request completes", () => {
        const wrapper = setupWrapper();
        expect(wrapper.vm.isLoading).toBe(true);
    });

    it("loads the returned file sources on mount", async () => {
        const expectedFileSources = [getFakeFileSource({ id: "foo" })];
        server.use(
            http.get(REMOTE_FILES_API_ROUTE, ({ response }) => {
                return response(200).json(expectedFileSources);
            }),
        );

        const wrapper = setupWrapper();

        expect(wrapper.vm.isLoading).toBe(true);

        await flushPromises();

        expect(wrapper.vm.isLoading).toBe(false);
        expect(wrapper.vm.fileSources).toEqual(expectedFileSources);
    });

    it("reports no writable source when every source is read-only", async () => {
        const expectedFileSources = [
            getFakeFileSource({ id: "foo", writable: false }),
            getFakeFileSource({ id: "bar", writable: false }),
        ];
        server.use(
            http.get(REMOTE_FILES_API_ROUTE, ({ response }) => {
                return response(200).json(expectedFileSources);
            }),
        );

        const wrapper = setupWrapper();

        await flushPromises();

        expect(wrapper.vm.hasWritable).toBe(false);
    });

    it("reports a writable source when one source is writable", async () => {
        const expectedFileSources = [
            getFakeFileSource({ id: "foo", writable: true }),
            getFakeFileSource({ id: "bar", writable: false }),
        ];
        server.use(
            http.get(REMOTE_FILES_API_ROUTE, ({ response }) => {
                return response(200).json(expectedFileSources);
            }),
        );

        const wrapper = setupWrapper();

        await flushPromises();

        expect(wrapper.vm.hasWritable).toBe(true);
    });
});
