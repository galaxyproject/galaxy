import { createTestingPinia } from "@pinia/testing";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { defineComponent } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import { type BrowsableFilesSourcePlugin } from "@/api/remoteFiles";

import { useFileSources } from "./fileSources";

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

function buildFakeFileSource(id: string, writable: boolean = true): BrowsableFilesSourcePlugin {
    const type = `${id}Type`;
    return {
        id: id,
        type,
        uri_root: `${type}://`,
        label: `${id} Label`,
        doc: `${id} Doc`,
        writable,
        browsable: true,
        supports: {
            pagination: false,
            search: false,
            sorting: false,
        },
    };
}

const { server, http } = useServerMock();

describe("useFileSources", () => {
    beforeEach(async () => {
        server.use(
            http.get(REMOTE_FILES_API_ROUTE, ({ response }) => {
                return response(200).json([]);
            })
        );
    });

    it("should be initially loading", async () => {
        const wrapper = setupWrapper();
        expect(wrapper.vm.isLoading).toBe(true);
    });

    it("should fetch file sources on mount", async () => {
        const expectedFileSources = [buildFakeFileSource("foo")];
        server.use(
            http.get(REMOTE_FILES_API_ROUTE, ({ response }) => {
                return response(200).json(expectedFileSources);
            })
        );

        const wrapper = setupWrapper();

        expect(wrapper.vm.isLoading).toBe(true);

        await flushPromises();

        expect(wrapper.vm.isLoading).toBe(false);
        expect(wrapper.vm.fileSources).toEqual(expectedFileSources);
    });

    it("should set hasWritable to false if no file sources are writable", async () => {
        const expectedFileSources = [buildFakeFileSource("foo", false), buildFakeFileSource("bar", false)];
        server.use(
            http.get(REMOTE_FILES_API_ROUTE, ({ response }) => {
                return response(200).json(expectedFileSources);
            })
        );

        const wrapper = setupWrapper();

        await flushPromises();

        expect(wrapper.vm.hasWritable).toEqual(false);
    });

    it("should set hasWritable to true if any file sources are writable", async () => {
        const expectedFileSources = [buildFakeFileSource("foo", true), buildFakeFileSource("bar", false)];
        server.use(
            http.get(REMOTE_FILES_API_ROUTE, ({ response }) => {
                return response(200).json(expectedFileSources);
            })
        );

        const wrapper = setupWrapper();

        await flushPromises();

        expect(wrapper.vm.hasWritable).toEqual(true);
    });
});
