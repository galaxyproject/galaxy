import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import Index from "./Index";

const localVue = getLocalVue();

jest.mock("components/Datatypes/factory");
jest.mock("./modules/services");
jest.mock("layout/modal");
jest.mock("onload/loadConfig");
jest.mock("./modules/utilities");
jest.mock("./modules/canvas");

jest.mock("app");

import { getDatatypesMapper } from "components/Datatypes/factory";
import { testDatatypesMapper } from "components/Datatypes/test_fixtures";
import { getVersions, loadWorkflow } from "./modules/services";
import { getStateUpgradeMessages } from "./modules/utilities";
import { getAppRoot } from "onload/loadConfig";
import WorkflowCanvas from "./modules/canvas";

getAppRoot.mockImplementation(() => "prefix/");

describe("Index", () => {
    let wrapper;

    beforeEach(() => {
        getDatatypesMapper.mockResolvedValue(testDatatypesMapper);
        getStateUpgradeMessages.mockImplementation(() => []);
        getVersions.mockResolvedValue((id) => []);
        WorkflowCanvas.mockClear();
    });

    async function mountAndWaitForCreated(workflow = {}) {
        loadWorkflow.mockResolvedValue(workflow);
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
        });
        await wrapper.vm.$nextTick();
        expect(WorkflowCanvas).toHaveBeenCalledTimes(1);
    }

    async function resetChanges() {
        wrapper.vm.hasChanges = false;
        await wrapper.vm.$nextTick();
    }

    it("resolved datatypes", async () => {
        mountAndWaitForCreated();
        expect(wrapper.datatypesMapper).not.toBeNull();
        expect(wrapper.datatypes).not.toBeNull();
        expect(wrapper.canvasManager).not.toBeNull();
    });

    it("routes to run to URL and respects Galaxy prefix", async () => {
        mountAndWaitForCreated();
        Object.defineProperty(window, "location", {
            value: "original",
            writable: true,
        });
        wrapper.vm.onRun();
        expect(window.location).toBe("prefix/workflows/run?id=workflow_id");
    });

    it("routes to run to download URL and respects Galaxy prefix", async () => {
        mountAndWaitForCreated();
        Object.defineProperty(window, "location", {
            value: "original",
            writable: true,
        });
        wrapper.vm.onDownload();
        expect(window.location).toBe("prefix/api/workflows/workflow_id/download?format=json-download");
    });

    it("tracks changes to annotations", async () => {
        mountAndWaitForCreated();
        expect(wrapper.hasChanges).toBeFalsy();
        await wrapper.setData({ annotation: "original annotation" });
        expect(wrapper.vm.hasChanges).toBeTruthy();

        resetChanges();

        await wrapper.setData({ annotation: "original annotation" });
        expect(wrapper.vm.hasChanges).toBeFalsy();

        await wrapper.setData({ annotation: "new annotation" });
        expect(wrapper.vm.hasChanges).toBeTruthy();
    });

    it("tracks changes to name", async () => {
        mountAndWaitForCreated();
        expect(wrapper.hasChanges).toBeFalsy();
        await wrapper.setData({ name: "original name" });
        expect(wrapper.vm.hasChanges).toBeTruthy();

        resetChanges();

        await wrapper.setData({ name: "original name" });
        expect(wrapper.vm.hasChanges).toBeFalsy();

        await wrapper.setData({ name: "new name" });
        expect(wrapper.vm.hasChanges).toBeTruthy();
    });

    it("prevents navigation only if hasChanges", async () => {
        mountAndWaitForCreated();
        expect(window.onbeforeunload()).toBeFalsy();
        wrapper.vm.onChange();
        expect(window.onbeforeunload()).toBeTruthy();
    });
});
