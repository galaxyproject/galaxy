import { expect, jest } from "@jest/globals";
import { createTestingPinia } from "@pinia/testing";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import { PiniaVuePlugin, setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
import type Vue from "vue";
import { nextTick } from "vue";

import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { getAppRoot } from "@/onload/loadConfig";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

import { getVersions, loadWorkflow } from "./modules/services";
import { getStateUpgradeMessages } from "./modules/utilities";

import Index from "./Index.vue";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

jest.mock("components/Datatypes/factory");
jest.mock("./modules/services");
jest.mock("layout/modal");
jest.mock("onload/loadConfig");
jest.mock("./modules/utilities");

jest.mock("app");

const mockGetAppRoot = getAppRoot as jest.Mocked<typeof getAppRoot>;
const mockGetStateUpgradeMessages = getStateUpgradeMessages as jest.Mock<typeof getStateUpgradeMessages>;
const mockLoadWorkflow = loadWorkflow as jest.Mocked<typeof loadWorkflow>;
const MockGetVersions = getVersions as jest.Mocked<typeof getVersions>;

describe("Index", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(() => {
        const testingPinia = createTestingPinia();
        setActivePinia(testingPinia);
        const datatypesStore = useDatatypesMapperStore();
        datatypesStore.datatypesMapper = testDatatypesMapper;
        mockLoadWorkflow.mockResolvedValue({ steps: {} });
        MockGetVersions.mockResolvedValue([]);
        mockGetStateUpgradeMessages.mockImplementation(() => []);
        mockGetAppRoot.mockImplementation(() => "prefix/");

        wrapper = shallowMount(Index, {
            propsData: {
                workflowId: "workflow_id",
                initialVersion: 1,
                workflowTags: ["moo", "cow"],
                moduleSections: [],
                dataManagers: [],
                workflows: [],
            },
            localVue,
            pinia: testingPinia,
        });
    });

    it("renders correctly", () => {
        expect(wrapper.exists()).toBe(true);
    });

    it("loads the workflow", async () => {
        await nextTick();

        expect(mockLoadWorkflow).toHaveBeenCalledWith({ id: "workflow_id", version: 1 });
    });
});
