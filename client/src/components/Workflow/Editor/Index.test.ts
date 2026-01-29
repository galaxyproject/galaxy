import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, mockUnprivilegedToolsRequest } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import { PiniaVuePlugin, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { getAppRoot } from "@/onload/loadConfig";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import type { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";

import { getVersions } from "./modules/services";
import { getStateUpgradeMessages } from "./modules/utilities";

import Index from "./Index.vue";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

vi.mock("components/Datatypes/factory", () => ({}));
vi.mock("./modules/services");
vi.mock("@/onload/loadConfig");
vi.mock("./modules/utilities");
vi.mock("@/components/Workflow/workflows.services");

vi.mock("app", () => ({}));

const { server, http } = useServerMock();

const mockGetAppRoot = vi.mocked(getAppRoot);
const mockGetStateUpgradeMessages = vi.mocked(getStateUpgradeMessages);
const mockLoadWorkflow = vi.mocked(getWorkflowFull);
const MockGetVersions = vi.mocked(getVersions);

/** TODO: A potentially hacky type until we modernize the entire
 * component to Composition API and TypeScript */
type IndexComponent = Vue & {
    annotation: string | null;
    name: string | null;
    stateStore: ReturnType<typeof useWorkflowStateStore>;
    datatypesMapper: ReturnType<typeof useDatatypesMapperStore> | null;
    datatypes: Record<string, string[]> | null;
    onDownload: () => void;
    onChange: () => void;
};

describe("Index", () => {
    let wrapper: Wrapper<IndexComponent>;

    beforeEach(() => {
        const testingPinia = createTestingPinia({ createSpy: vi.fn });
        setActivePinia(testingPinia);
        const datatypesStore = useDatatypesMapperStore();
        datatypesStore.datatypesMapper = testDatatypesMapper;
        mockLoadWorkflow.mockResolvedValue({ steps: {} });
        MockGetVersions.mockResolvedValue([]);
        mockGetStateUpgradeMessages.mockImplementation(() => []);
        mockGetAppRoot.mockImplementation(() => "prefix/");
        Object.defineProperty(window, "onbeforeunload", {
            value: null,
            writable: true,
        });
        mockUnprivilegedToolsRequest(server, http);
        wrapper = shallowMount(Index as object, {
            propsData: {
                workflowId: "workflow_id",
                initialVersion: 1,
                workflowTags: ["moo", "cow"],
                workflows: [],
                toolbox: [],
            },
            localVue,
            pinia: testingPinia,
            // mock out components that have exposed methods used by Index.vue.
            stubs: {
                ActivityBar: {
                    template: "<div />",
                    methods: {
                        isActiveSideBar(name: string) {
                            return name === "workflow-editor-tools";
                        },
                    },
                    expose: ["isActiveSideBar"],
                },
                WorkflowGraph: {
                    template: "<div />",
                    methods: {
                        fitWorkflow() {},
                    },
                    expose: ["fitWorkflow"],
                },
            },
        });
    });

    // Methods to handle the `hasChanges` ref. Once we modernize, we can just use the store directly.
    function getHasChanges() {
        return wrapper.vm.stateStore.hasChanges;
    }
    async function resetChanges() {
        setHasChanges(false);
        await wrapper.vm.$nextTick();
    }
    function setHasChanges(value: boolean) {
        wrapper.vm.stateStore.hasChanges = value;
    }

    it("resolves datatypes", async () => {
        expect(wrapper.vm.datatypesMapper).not.toBeNull();
        expect(wrapper.vm.datatypes).not.toBeNull();
    });

    it("routes to download URL and respects Galaxy prefix", async () => {
        Object.defineProperty(window, "location", {
            value: "original",
            writable: true,
        });
        wrapper.vm.onDownload();
        expect(window.location).toBe("prefix/api/workflows/workflow_id/download?format=json-download");
    });

    it("tracks changes to annotations", async () => {
        expect(getHasChanges()).toBeFalsy();
        wrapper.vm.annotation = "original annotation";
        await wrapper.vm.$nextTick();
        expect(getHasChanges()).toBeTruthy();

        await resetChanges();

        wrapper.vm.annotation = "original annotation";
        await wrapper.vm.$nextTick();
        expect(getHasChanges()).toBeFalsy();

        wrapper.vm.annotation = "new annotation";
        await wrapper.vm.$nextTick();
        expect(getHasChanges()).toBeTruthy();
    });

    it("tracks changes to name", async () => {
        expect(getHasChanges()).toBeFalsy();
        wrapper.vm.name = "original name";
        await wrapper.vm.$nextTick();
        expect(getHasChanges()).toBeTruthy();

        await resetChanges();

        wrapper.vm.name = "original name";
        await wrapper.vm.$nextTick();
        expect(getHasChanges()).toBeFalsy();

        wrapper.vm.name = "new name";
        await wrapper.vm.$nextTick();
        expect(getHasChanges()).toBeTruthy();
    });

    it("prevents navigation only if hasChanges", async () => {
        expect(getHasChanges()).toBeFalsy();
        await wrapper.vm.onChange();
        const confirmationRequired = wrapper.emitted()["update:confirmation"]![0]![0];
        expect(confirmationRequired).toBeTruthy();
    });
});
