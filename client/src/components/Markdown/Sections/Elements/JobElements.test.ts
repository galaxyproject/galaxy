import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { ShowFullJobResponse } from "@/api/jobs";
import { useJobStore } from "@/stores/jobStore";

import JobMetrics from "./JobMetrics.vue";
import JobParameters from "./JobParameters.vue";
import ToolLinkPopover from "@/components/Tool/ToolLinkPopover.vue";

// Translates only what a test asks for, so the other assertions see the source strings.
const translations = vi.hoisted(() => ({}) as Record<string, string>);
vi.mock("@/utils/localization", async (importOriginal) => {
    const actual = await importOriginal<{ localize: (text: string) => string }>();
    const localize = (text: string) => translations[text] ?? actual.localize(text);
    return { ...actual, default: localize, localize };
});

const localVue = getLocalVue();
// Keeps requests the imported stores make off the network.
useServerMock();

let wrapper: VueWrapper | undefined;

afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    Object.keys(translations).forEach((text) => delete translations[text]);
});

describe.each([
    { name: "JobMetrics", component: JobMetrics },
    { name: "JobParameters", component: JobParameters },
])("$name", ({ component }) => {
    function mountElement(toolId?: string) {
        const pinia = createTestingPinia({ createSpy: vi.fn });
        // The testing store stubs fetchJob, so stand in for the job it would have loaded.
        // `useJobDetails` reads the passive `getCachedJob` getter, not `getJob` (which also
        // triggers a fetch on a cache miss).
        // @ts-expect-error: getters are only writable on a testing store
        useJobStore(pinia).getCachedJob = () => (toolId ? ({ tool_id: toolId } as ShowFullJobResponse) : null);
        wrapper = mount(component as object, {
            props: { jobId: "job_id", title: "Job" },
            global: {
                ...withPlugins(localVue, pinia),
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
        return wrapper;
    }

    it("anchors the tool popover to a named button so keyboard users can open it", () => {
        const element = mountElement("cat1");

        const button = element.find("button[aria-label='Tool details']");
        const popover = element.findComponent(ToolLinkPopover);
        const target = (popover.props("target") as () => { $el?: Element })();

        expect(button.exists()).toBe(true);
        expect(target.$el ?? target).toBe(button.element);
        expect(popover.props("interactive")).toBe(true);
    });

    it("localizes the tool details button's accessible name", () => {
        translations["Tool details"] = "Werkzeugdetails";

        expect(mountElement("cat1").find("button[aria-label='Werkzeugdetails']").exists()).toBe(true);
    });

    it("shows no tool details button until the job's tool is known", () => {
        const element = mountElement();

        expect(element.find("button[aria-label='Tool details']").exists()).toBe(false);
    });
});
