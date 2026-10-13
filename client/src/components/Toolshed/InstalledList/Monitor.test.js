import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import Monitor from "./Monitor.vue";

vi.mock("app");
vi.mock("onload/loadConfig", () => ({
    getAppRoot: vi.fn(() => "/"),
}));

const { getInstalledRepositories } = vi.hoisted(() => ({
    getInstalledRepositories: vi.fn(async () => [
        {
            name: "name_0",
            owner: "owner_0",
            status: "status_0_0",
            description: "description_0_0",
        },
        {
            name: "name_1",
            owner: "owner_1",
            status: "status_1",
            description: "description_1",
        },
    ]),
}));

vi.mock("../services", () => ({
    Services: class Services {
        getInstalledRepositories(...args) {
            return getInstalledRepositories(...args);
        }
    },
}));

describe("Monitor", () => {
    it("test monitor", async () => {
        const wrapper = mount(Monitor);

        await flushPromises();

        const headers = wrapper.findAll("th");
        expect(headers.length).toBe(0);

        const cells = wrapper.findAll("td");
        expect(cells.length).toBe(6);
        expect(cells.at(0).text()).toContain("name_0 (owner_0)");
        expect(cells.at(1).text()).toContain("status_0_0");
        expect(cells.at(3).text()).toContain("name_1 (owner_1)");
        expect(cells.at(4).text()).toContain("status_1");
        wrapper.unmount();
    });

    it("stops polling once unmounted", async () => {
        vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
        try {
            getInstalledRepositories.mockClear();
            const wrapper = mount(Monitor);
            await flushPromises();
            expect(getInstalledRepositories).toHaveBeenCalledTimes(1);

            vi.advanceTimersByTime(5000);
            await flushPromises();
            expect(getInstalledRepositories).toHaveBeenCalledTimes(2);

            wrapper.unmount();
            vi.advanceTimersByTime(15000);
            await flushPromises();
            expect(getInstalledRepositories).toHaveBeenCalledTimes(2);
        } finally {
            vi.useRealTimers();
        }
    });

    it("does not resume polling when a request resolves after unmount", async () => {
        vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
        try {
            getInstalledRepositories.mockClear();
            const wrapper = mount(Monitor);
            await flushPromises();

            let resolvePending;
            getInstalledRepositories.mockImplementationOnce(() => new Promise((resolve) => (resolvePending = resolve)));
            vi.advanceTimersByTime(5000);
            await flushPromises();
            expect(getInstalledRepositories).toHaveBeenCalledTimes(2);

            wrapper.unmount();
            resolvePending([]);
            await flushPromises();
            vi.advanceTimersByTime(15000);
            await flushPromises();
            expect(getInstalledRepositories).toHaveBeenCalledTimes(2);
        } finally {
            vi.useRealTimers();
        }
    });

    it("stops polling after a request fails, even when the tab is shown again", async () => {
        vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
        const visibility = vi.spyOn(document, "visibilityState", "get");
        try {
            getInstalledRepositories.mockClear();
            getInstalledRepositories.mockRejectedValueOnce(new Error("boom"));
            const wrapper = mount(Monitor);
            await flushPromises();
            expect(wrapper.find(".alert-danger").text()).toContain("boom");

            for (const state of ["hidden", "visible"]) {
                visibility.mockReturnValue(state);
                document.dispatchEvent(new Event("visibilitychange"));
            }
            vi.advanceTimersByTime(15000);
            await flushPromises();
            expect(getInstalledRepositories).toHaveBeenCalledTimes(1);
            wrapper.unmount();
        } finally {
            visibility.mockRestore();
            vi.useRealTimers();
        }
    });
});
