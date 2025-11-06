import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { GalaxyApi } from "@/api";

import DisplayApplicationCreateLink from "./DisplayApplication.vue";

jest.mock("@/api", () => {
    const post = jest.fn();
    return {
        GalaxyApi: jest.fn(() => ({
            POST: post,
        })),
    };
});

const localVue = getLocalVue();

beforeEach(() => {
    jest.clearAllMocks();
    delete window.open;
    window.open = jest.fn();
});

it("renders success with resource and opens window", async () => {
    GalaxyApi().POST.mockResolvedValueOnce({
        data: {
            resource: "http://example.com/res",
            messages: [],
            refresh: false,
        },
        error: null,
    });
    const wrapper = mount(DisplayApplicationCreateLink, {
        localVue,
        propsData: {
            appName: "igv",
            datasetId: "1",
            linkName: "local_default",
        },
    });
    await flushPromises();
    await wrapper.vm.$nextTick();
    expect(window.open).toHaveBeenCalledWith("http://example.com/res", "_blank");
    expect(wrapper.text()).toContain("Display application is ready");
    expect(wrapper.text()).toContain("http://example.com");
});

it("handles refresh loop once", async () => {
    jest.useFakeTimers();
    GalaxyApi()
        .POST.mockResolvedValueOnce({
            data: {
                refresh: true,
                messages: [["Waiting", "info"]],
                resource: null,
            },
            error: null,
        })
        .mockResolvedValueOnce({
            data: {
                resource: "http://example.com/final",
                refresh: false,
                messages: [],
            },
            error: null,
        });
    const wrapper = mount(DisplayApplicationCreateLink, {
        localVue,
        propsData: {
            appName: "igv",
            datasetId: "1",
            linkName: "local_default",
        },
    });
    await flushPromises();
    await wrapper.vm.$nextTick();
    jest.runOnlyPendingTimers();
    await flushPromises();
    await wrapper.vm.$nextTick();
    expect(window.open).toHaveBeenCalledWith("http://example.com/final", "_blank");
});

it("renders error", async () => {
    GalaxyApi().POST.mockResolvedValueOnce({
        data: null,
        error: { err_msg: "Failed" },
    });
    const wrapper = mount(DisplayApplicationCreateLink, {
        localVue,
        propsData: {
            appName: "igv",
            datasetId: "1",
            linkName: "local_default",
        },
    });
    await flushPromises();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("Failed to create link");
});

it("renders initialization steps", async () => {
    GalaxyApi().POST.mockResolvedValueOnce({
        data: {
            refresh: false,
            resource: null,
            messages: [["Preparing", "info"]],
            preparable_steps: [
                { name: "alpha", ready: false, state: "running" },
                { name: "beta", ready: true, state: "ok" },
            ],
        },
        error: null,
    });
    const wrapper = mount(DisplayApplicationCreateLink, {
        localVue,
        propsData: {
            appName: "igv",
            datasetId: "1",
            linkName: "local_default",
        },
    });
    await flushPromises();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("Display Application Initialization");
    expect(wrapper.text()).toContain("alpha");
    expect(wrapper.text()).toContain("running");
    expect(wrapper.text()).toContain("beta");
    expect(wrapper.text()).toContain("ok");
    expect(window.open).not.toHaveBeenCalled();
});
