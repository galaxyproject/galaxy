import { expect, jest } from "@jest/globals";

import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { PiniaVuePlugin } from "pinia";
import { setActivePinia } from "pinia";
import { createTestingPinia } from "@pinia/testing";

import Index from "./Index.vue";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

jest.mock("components/Datatypes/factory");
jest.mock("./modules/services");
jest.mock("layout/modal");
jest.mock("onload/loadConfig");
jest.mock("./modules/utilities");

jest.mock("app");

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { loadWorkflow, getVersions } from "./modules/services";
import { getStateUpgradeMessages } from "./modules/utilities";
import { getAppRoot } from "@/onload/loadConfig";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

const mockGetAppRoot = getAppRoot as jest.Mocked<typeof getAppRoot>;
const mockGetStateUpgradeMessages = getStateUpgradeMessages as jest.Mock<typeof getStateUpgradeMessages>;
const mockLoadWorkflow = loadWorkflow as jest.Mocked<typeof loadWorkflow>;
const MockGetVersions = getVersions as jest.Mocked<typeof getVersions>;

describe("Index", () => {
    let wrapper: any; // don't know how to add type hints here, see https://github.com/vuejs/vue-test-utils/issues/255

    beforeEach(() => {
        const testingPinia = createTestingPinia();
        setActivePinia(testingPinia);
        const datatypesStore = useDatatypesMapperStore();
        datatypesStore.datatypesMapper = testDatatypesMapper;
        mockLoadWorkflow.mockResolvedValue({ steps: {} });
        MockGetVersions.mockResolvedValue(() => []);
        mockGetStateUpgradeMessages.mockImplementation(() => []);
        mockGetAppRoot.mockImplementation(() => "prefix/");
        Object.defineProperty(window, "onbeforeunload", {
            value: null,
            writable: true,
        });
        wrapper = shallowMount(Index, {
            propsData: {
                id: "workflow_id",
                initialVersion: 1,
                tags: ["moo", "cow"],
                moduleSections: [],
                dataManagers: [],
                workflows: [],
                toolbox: [],
            },
            localVue,
            pinia: testingPinia,
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
