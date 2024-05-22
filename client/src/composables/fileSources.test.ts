import { createTestingPinia } from "@pinia/testing";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { defineComponent } from "vue";

import { mockFetcher } from "@/api/schema/__mocks__";

import { useFileSources } from "./fileSources";

jest.mock("@/api/schema");

const REMOTE_FILES_API_ROUTE = "/api/remote_files/plugins";

const TestComponent = defineComponent({
    setup() {
        return {
            // Call the composable and expose all return values into our
            // component instance so we can access them with wrapper.vm
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

function setupWrapper(): any {
    const pinia = createTestingPinia({ stubActions: false });
    return shallowMount(TestComponent, { pinia });
}

describe("useFileSources", () => {
    beforeEach(async () => {
        mockFetcher.path(REMOTE_FILES_API_ROUTE).method("get").mock({ data: [] });
    });

    it("should be initially loading", async () => {
        const wrapper = setupWrapper();
        expect(wrapper.vm.isLoading).toBe(true);
    });

    it("should fetch file sources on mount", async () => {
        const expectedFileSources = [{ id: "foo", writable: true }];
        mockFetcher.path(REMOTE_FILES_API_ROUTE).method("get").mock({ data: expectedFileSources });

        const wrapper = setupWrapper();

        expect(wrapper.vm.isLoading).toBe(true);

        await flushPromises();

        expect(wrapper.vm.isLoading).toBe(false);
        expect(wrapper.vm.fileSources).toEqual(expectedFileSources);
    });

    it("should set hasWritable to false if no file sources are writable", async () => {
        const expectedFileSources = [
            { id: "foo", writable: false },
            { id: "bar", writable: false },
        ];
        mockFetcher.path(REMOTE_FILES_API_ROUTE).method("get").mock({ data: expectedFileSources });

        const wrapper = setupWrapper();

        await flushPromises();

        expect(wrapper.vm.hasWritable).toEqual(false);
    });

    it("should set hasWritable to true if any file sources are writable", async () => {
        const expectedFileSources = [
            { id: "foo", writable: true },
            { id: "bar", writable: false },
        ];
        mockFetcher.path(REMOTE_FILES_API_ROUTE).method("get").mock({ data: expectedFileSources });

        const wrapper = setupWrapper();

        await flushPromises();

        expect(wrapper.vm.hasWritable).toEqual(true);
    });
});
