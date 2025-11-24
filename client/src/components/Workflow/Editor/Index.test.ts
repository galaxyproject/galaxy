import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, mockUnprivilegedToolsRequest } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { PiniaVuePlugin, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { getAppRoot } from "@/onload/loadConfig";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

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

describe("Index", () => {
    let wrapper: any; // don't know how to add type hints here, see https://github.com/vuejs/vue-test-utils/issues/255

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

    async function resetChanges() {
        wrapper.vm.hasChanges = false;
        await wrapper.vm.$nextTick();
    }

    it("resolves datatypes", async () => {
        expect(wrapper.datatypesMapper).not.toBeNull();
        expect(wrapper.datatypes).not.toBeNull();
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
        expect(wrapper.vm.hasChanges).toBeFalsy();
        wrapper.vm.annotation = "original annotation";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.hasChanges).toBeTruthy();

        resetChanges();

        wrapper.vm.annotation = "original annotation";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.hasChanges).toBeFalsy();

        wrapper.vm.annotation = "new annotation";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.hasChanges).toBeTruthy();
    });

    it("tracks changes to name", async () => {
        expect(wrapper.hasChanges).toBeFalsy();
        wrapper.vm.name = "original name";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.hasChanges).toBeTruthy();

        resetChanges();

        wrapper.vm.name = "original name";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.hasChanges).toBeFalsy();

        wrapper.vm.name = "new name";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.hasChanges).toBeTruthy();
    });

    it("prevents navigation only if hasChanges", async () => {
        expect(wrapper.vm.hasChanges).toBeFalsy();
        await wrapper.vm.onChange();
        const confirmationRequired = wrapper.emitted()["update:confirmation"][0][0];
        expect(confirmationRequired).toBeTruthy();
    });
});
