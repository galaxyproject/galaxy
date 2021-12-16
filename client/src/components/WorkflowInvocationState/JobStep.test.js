import BootstrapVue from "bootstrap-vue";
import JobStep from "./JobStep";
import { mount } from "@vue/test-utils";
import jobs from "./test/json/jobs.json";

jest.mock("components/providers/History/caching");

import { createLocalVue } from "@vue/test-utils";

// create an extended `Vue` constructor
const localVue = createLocalVue();

// install plugins as normal
localVue.use(BootstrapVue);

describe("DatasetUIWrapper.vue with Dataset", () => {
    let wrapper;
    let propsData;

    beforeEach(async () => {
        propsData = {
            jobs: jobs,
        };
        wrapper = mount(JobStep, {
            localVue,
            propsData,
            stubs: {
                JobProvider: { template: "<div class='expanded'>I am expanded</div>" },
            },
        });
    });
    test("it renders a table with 2 jobs", async () => {
        expect(wrapper.find("tbody").findAll("tr").length).toBe(2);
    });
    test("it expands on row click", async () => {
        // verify no item is expanded
        expect(wrapper.vm.toggledItems["1"]).toBe(undefined);
        expect(wrapper.find(".expanded").exists()).toBeFalsy();
        // expand
        wrapper.find("tbody").find("tbody").find("tr").trigger("click");
        await localVue.nextTick();
        expect(wrapper.vm.toggledItems["1"]).toBeTruthy();
        expect(wrapper.find(".expanded").exists()).toBeTruthy();
        wrapper.find("tbody").find("tbody").find("tr").trigger("click");
        // close again
        await localVue.nextTick();
        expect(wrapper.vm.toggledItems["1"]).toBeFalsy();
        expect(wrapper.find(".expanded").exists()).toBeFalsy();
    });
    test("it sustains expanded on prop update", async () => {
        // verify no item is expanded
        expect(wrapper.vm.toggledItems["1"]).toBe(undefined);
        expect(wrapper.find(".expanded").exists()).toBeFalsy();
        // expand
        wrapper.find("tbody").find("tbody").find("tr").trigger("click");
        await localVue.nextTick();
        expect(wrapper.vm.toggledItems["1"]).toBeTruthy();
        expect(wrapper.find(".expanded").exists()).toBeTruthy();
        // 2 collapsed rows, plus 1 expanded row
        expect(wrapper.find("tbody").findAll("tr").length).toBe(3);
        // update data
        const additionalJob = { ...jobs[0], id: 3 };
        wrapper.setProps({ jobs: [...jobs, additionalJob] });
        await localVue.nextTick();
        // verify new data is displayed
        expect(wrapper.find("tbody").findAll("tr").length).toBe(4);
        // verify first row is still expanded
        expect(wrapper.vm.toggledItems["1"]).toBeTruthy();
        expect(wrapper.find(".expanded").exists()).toBeTruthy();
    });
});
