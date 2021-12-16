import Invocations from "../Workflow/Invocations";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import flushPromises from "flush-promises";

import RecentInvocations from "./RecentInvocations.vue";

jest.mock("components/providers/History/caching");
jest.mock("./UserServices");

const localVue = getLocalVue();

describe("RecentInvocations.vue", () => {
    let wrapper;
    let fetchInvocationsSpy;

    beforeEach(async () => {
        fetchInvocationsSpy = jest.spyOn(RecentInvocations.methods, "fetchRecentInvocations");
        wrapper = mount(RecentInvocations, { localVue });
        await flushPromises();
    });

    it("loading should be false", async () => {
        expect(wrapper.vm.loading).toBeFalsy();
        expect(fetchInvocationsSpy).toHaveBeenCalled();
    });

    it("invocationItems should be empty", async () => {
        expect(wrapper.vm.invocationItems).toHaveLength(0);
    });

    it("should show no invocation message", async () => {
        // message should exist
        expect(wrapper.text()).toContain("There are no invocations to be shown.");
    });

    it("should call fetchInvocationItems on event", async () => {
        wrapper.findComponent(Invocations).vm.$emit("reload-invocations");
        expect(fetchInvocationsSpy).toHaveBeenCalledTimes(2);
    });
});
