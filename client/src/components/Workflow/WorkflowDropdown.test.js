import WorkflowDropdown from "./WorkflowDropdown";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";

const localVue = getLocalVue(true);

const TEST_WORKFLOW_NAME = "my workflow";
const TEST_WORKFLOW_DESCRIPTION = "my cool workflow description";

describe("WorkflowDropdown.vue", () => {
    let wrapper;
    let propsData;

    function initWrapperForWorkflow(workflow) {
        propsData = {
            root: "/root/",
            workflow: workflow,
        };
        wrapper = shallowMount(WorkflowDropdown, {
            propsData,
            localVue,
        });
    }

    function workflowOptions() {
        return wrapper.findAll(".dropdown-menu .dropdown-item");
    }

    describe("for workflows owned by user", () => {
        beforeEach(async () => {
            const workflow = {
                name: TEST_WORKFLOW_NAME,
                id: "workflowid123",
                description: TEST_WORKFLOW_DESCRIPTION,
                owner: "test",
            };
            initWrapperForWorkflow(workflow);
        });

        it("should not display source metadata if not present", async () => {
            expect(wrapper.find(".workflow-trs-icon").exists()).toBeFalsy();
            expect(wrapper.find(".workflow-external-link").exists()).toBeFalsy();
        });

        it("should display name and description", async () => {
            expect(wrapper.find(".workflow-dropdown-name").text()).toBe(TEST_WORKFLOW_NAME);
            expect(wrapper.find(".workflow-dropdown-description").text()).toBe(TEST_WORKFLOW_DESCRIPTION);
        });

        it("should provide all owner workflow options", () => {
            expect(workflowOptions().length).toBeGreaterThan(2);
        });
    });

    describe("workflows without annotations", () => {
        beforeEach(async () => {
            const workflow = {
                name: TEST_WORKFLOW_NAME,
                id: "workflowid123",
                owner: "test",
            };
            initWrapperForWorkflow(workflow);
        });

        it("should display name but not description", async () => {
            expect(wrapper.find(".workflow-dropdown-name").text()).toBe(TEST_WORKFLOW_NAME);
            expect(wrapper.find(".workflow-dropdown-description").exists()).toBeFalsy();
        });
    });

    describe("for workflows shared with user", () => {
        beforeEach(async () => {
            const workflow = {
                name: TEST_WORKFLOW_NAME,
                id: "workflowid123",
                description: TEST_WORKFLOW_DESCRIPTION,
                shared: true,
            };
            initWrapperForWorkflow(workflow);
        });

        it("should provide a limited number of options", () => {
            expect(workflowOptions().length).toBe(3);
            expect(workflowOptions().at(0).text()).toBeLocalizationOf("Copy");
            expect(workflowOptions().at(1).text()).toBeLocalizationOf("Download");
            expect(workflowOptions().at(2).text()).toBeLocalizationOf("View");
        });
    });
});
