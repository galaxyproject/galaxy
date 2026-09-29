import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import ToolEntryPoints from "./ToolEntryPoints.vue";

describe("ToolEntryPoints/ToolEntryPoints.vue", () => {
    const localVue = getLocalVue();
    const router = injectTestRouter(localVue);
    const INACTIVE_ITS = [
        {
            model_class: "InteractiveToolEntryPoint",
            id: "52e496b945151ee8",
            job_id: "52e496b945151ee8",
            name: "Jupyter Interactive Tool",
            active: false,
            created_time: "2020-02-24T15:59:18.122103",
            modified_time: "2020-02-24T15:59:20.428594",
            target: "http://52e496b945151ee8-be8a5bee5d5849a5b4e035b51305256e.interactivetoolentrypoint.interactivetool.localhost:8080/ipython/lab",
        },
        {
            model_class: "InteractiveToolEntryPoint",
            id: "b887d74393f85b6d",
            job_id: "52e496b945151ee8",
            name: "AskOmics instance on None",
            active: false,
            created_time: "2020-01-24T15:59:22.406480",
            modified_time: "2020-02-24T15:59:24.757453",
            target: "http://b887d74393f85b6d-b1fd3f42331a49c1b3d8a4d1b27240b8.interactivetoolentrypoint.interactivetool.localhost:8080/loginapikey/oleg",
        },
        {
            model_class: "InteractiveToolEntryPoint",
            id: "b887d74393f85b6d",
            job_id: "b887d74393f85b6d",
            name: "AskOmics instance on None",
            active: true,
            created_time: "2020-01-24T15:59:22.406480",
            modified_time: "2020-02-24T15:59:24.757453",
            target: "http://b887d74393f85b6d-b1fd3f42331a49c1b3d8a4d1b27240b8.interactivetoolentrypoint.interactivetool.localhost:8080/loginapikey/oleg",
        },
    ];
    const ACTIVE_ITS = INACTIVE_ITS.map((obj, i) => {
        return { ...obj, active: true };
    });
    let wrapper;
    let testPinia;

    it("should render list when result are ready but views are not active yet", async () => {
        testPinia = createTestingPinia({
            createSpy: vi.fn,
            initialState: {
                entryPointStore: {
                    entryPoints: INACTIVE_ITS,
                },
            },
        });
        setActivePinia(testPinia);
        wrapper = mount(ToolEntryPoints, {
            props: {
                jobId: "52e496b945151ee8",
            },
            global: localVue,
            pinia: testPinia,
            router,
        });
        const buttons = wrapper.findAll("[data-description='entry point button']");
        expect(buttons.length).toBe(2);
        buttons.wrappers.forEach((button) => {
            expect(button.element.tagName).toBe("BUTTON");
            expect(button.attributes("aria-disabled")).toBe("true");
        });
    });

    it("should render links when tools are active", async () => {
        testPinia = createTestingPinia({
            createSpy: vi.fn,
            initialState: {
                entryPointStore: {
                    entryPoints: ACTIVE_ITS,
                },
            },
        });
        setActivePinia(testPinia);
        wrapper = mount(ToolEntryPoints, {
            props: {
                jobId: "52e496b945151ee8",
            },
            global: localVue,
            pinia: testPinia,
            router,
        });
        const links = wrapper.findAll("a[data-description='entry point button']");
        expect(links.length).toBe(2);
        expect(links.wrappers.map((link) => link.attributes("href"))).toEqual(
            ACTIVE_ITS.slice(0, 2).map((entryPoint) => entryPoint.target),
        );
    });

    it("should open a single active tool in a new tab", async () => {
        testPinia = createTestingPinia({
            createSpy: vi.fn,
            initialState: {
                entryPointStore: {
                    entryPoints: ACTIVE_ITS,
                },
            },
        });
        setActivePinia(testPinia);
        wrapper = mount(ToolEntryPoints, {
            propsData: {
                jobId: "b887d74393f85b6d",
            },
            localVue,
            pinia: testPinia,
            router,
        });
        const link = wrapper.find(`a[href='${ACTIVE_ITS[2].target}']`);
        expect(link.exists()).toBe(true);
        expect(link.attributes("target")).toBe("_blank");
    });
});
