import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import JobMetrics from "./JobMetrics.vue";
import JobParameters from "./JobParameters.vue";
import ToolLinkPopover from "@/components/Tool/ToolLinkPopover.vue";

const localVue = getLocalVue();
// Keeps requests the imported stores make off the network.
useServerMock();

let wrapper: VueWrapper | undefined;

afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
});

describe.each([
    { name: "JobMetrics", component: JobMetrics },
    { name: "JobParameters", component: JobParameters },
])("$name", ({ component }) => {
    it("anchors the tool popover to a named button so keyboard users can open it", () => {
        wrapper = mount(component as object, {
            props: { jobId: "job_id", title: "Job" },
            global: {
                ...withPlugins(localVue, createTestingPinia({ createSpy: vi.fn })),
                stubs: {
                    ...localVue.stubs,
                    // The card's `nobody` attribute draws a Vue tip that is beside the point here.
                    BCard: { template: "<div><slot /></div>" },
                    JobMetrics: true,
                    JobParameters: true,
                    JobSelection: true,
                    ToolLinkPopover: true,
                },
            },
        });

        const button = wrapper.find("button[aria-label='Tool details']");
        const popover = wrapper.findComponent(ToolLinkPopover);
        const target = (popover.props("target") as () => { $el?: Element })();

        expect(button.exists()).toBe(true);
        expect(target.$el ?? target).toBe(button.element);
        expect(popover.props("interactive")).toBe(true);
    });
});
