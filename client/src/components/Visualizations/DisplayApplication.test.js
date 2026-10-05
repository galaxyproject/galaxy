import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, expect, it, vi } from "vitest";

import { GalaxyApi } from "@/api";

import DisplayApplicationCreateLink from "./DisplayApplication.vue";

vi.mock("@/api", () => {
    const post = vi.fn();
    return {
        GalaxyApi: vi.fn(() => ({
            POST: post,
        })),
    };
});

const localVue = getLocalVue();

beforeEach(() => {
    vi.clearAllMocks();
    delete window.open;
    window.open = vi.fn();
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
        global: localVue,
        props: {
            appName: "igv",
            datasetId: "1",
            linkName: "local_default",
        },
    });
    await flushPromises();
    expect(window.open).toHaveBeenCalledWith("http://example.com/res", "_blank");
    expect(wrapper.text()).toContain("Display application is ready");
    expect(wrapper.text()).toContain("http://example.com");
});

it("handles refresh loop once", async () => {
    vi.useFakeTimers();
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
    mount(DisplayApplicationCreateLink, {
        global: localVue,
        props: {
            appName: "igv",
            datasetId: "1",
            linkName: "local_default",
        },
    });
    await flushPromises();
    vi.runOnlyPendingTimers();
    await flushPromises();
    expect(window.open).toHaveBeenCalledWith("http://example.com/final", "_blank");
});

it("renders error", async () => {
    GalaxyApi().POST.mockResolvedValueOnce({
        data: null,
        error: { err_msg: "Failed" },
    });
    const wrapper = mount(DisplayApplicationCreateLink, {
        global: localVue,
        props: {
            appName: "igv",
            datasetId: "1",
            linkName: "local_default",
        },
    });
    await flushPromises();
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
        global: localVue,
        props: {
            appName: "igv",
            datasetId: "1",
            linkName: "local_default",
        },
    });
    await flushPromises();
    expect(wrapper.text()).toContain("Display Application Initialization");
    expect(wrapper.text()).toContain("alpha");
    expect(wrapper.text()).toContain("running");
    expect(wrapper.text()).toContain("beta");
    expect(wrapper.text()).toContain("ok");
    expect(window.open).not.toHaveBeenCalled();
});
