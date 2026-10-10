import { createTestingPinia } from "@pinia/testing";
import { createTestRouter, getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import entryPointsResponse from "@/components/InteractiveTools/testData/testInteractiveToolsResponse";

import ToolEntryPoints from "./ToolEntryPoints.vue";

const MULTI_TOOL_JOB_ID = "52e496b945151ee8";
const SINGLE_TOOL_JOB_ID = "b887d74393f85b6d";

enableAutoUnmount(afterEach);

function mountEntryPoints({ active = false, jobId = MULTI_TOOL_JOB_ID } = {}) {
    // The first job has two sessions; the third session belongs to another job.
    const entryPoints = [
        { ...entryPointsResponse[0], job_id: MULTI_TOOL_JOB_ID, active },
        { ...entryPointsResponse[1], job_id: MULTI_TOOL_JOB_ID, active },
        { ...entryPointsResponse[1], job_id: SINGLE_TOOL_JOB_ID, active: true },
    ];
    const localVue = getLocalVue();
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        initialState: { entryPointStore: { entryPoints } },
    });
    setActivePinia(pinia);
    const wrapper = mount(ToolEntryPoints, {
        props: { jobId },
        global: withPlugins(localVue, pinia, createTestRouter()),
    });
    return { wrapper, entryPoints };
}

describe("ToolEntryPoints", () => {
    it("renders two disabled buttons for a job whose sessions are not active yet", () => {
        const { wrapper } = mountEntryPoints();
        const buttons = wrapper.findAll("[data-description='entry point button']");
        expect(buttons).toHaveLength(2);
        for (const button of buttons) {
            expect(button.element.tagName).toBe("BUTTON");
            expect(button.attributes("aria-disabled")).toBe("true");
        }
    });

    it("renders links to both active sessions belonging to the job", () => {
        const { wrapper, entryPoints } = mountEntryPoints({ active: true });
        const links = wrapper.findAll("a[data-description='entry point button']");
        expect(links).toHaveLength(2);
        expect(links.map((link) => link.attributes("href"))).toEqual(
            entryPoints.slice(0, 2).map((entryPoint) => entryPoint.target),
        );
    });

    it("opens a job's single active session in a new tab", () => {
        const { wrapper, entryPoints } = mountEntryPoints({ active: true, jobId: SINGLE_TOOL_JOB_ID });
        const link = wrapper.find(`a[href='${entryPoints[2].target}']`);
        expect(link.exists()).toBe(true);
        expect(link.attributes("target")).toBe("_blank");
    });
});
