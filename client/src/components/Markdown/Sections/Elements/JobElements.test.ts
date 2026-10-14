import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { ShowFullJobResponse } from "@/api/jobs";
import { useJobStore } from "@/stores/jobStore";

import JobMetrics from "./JobMetrics.vue";
import JobParameters from "./JobParameters.vue";

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
    document.body.innerHTML = "";
    Object.keys(translations).forEach((text) => delete translations[text]);
});

describe.each([
    { name: "JobMetrics", component: JobMetrics },
    { name: "JobParameters", component: JobParameters },
])("$name", ({ component }) => {
    async function mountElement(toolId?: string) {
        const pinia = createTestingPinia({ createSpy: vi.fn });
        // The testing store stubs fetchJob, so stand in for the job it would have loaded.
        // @ts-expect-error: getters are only writable on a testing store
        useJobStore(pinia).getJob = () => (toolId ? ({ tool_id: toolId } as ShowFullJobResponse) : null);
        wrapper = mount(component as object, {
            attachTo: document.body,
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
                    // Fetches the tool's name, which these tests don't need.
                    ToolLink: true,
                },
            },
        });
        // The popover binds to its button on the tick after mounting.
        await nextTick();
        await nextTick();
        return wrapper;
    }

    it("renders the tool details button inline after the title, controlling the tool dialog", async () => {
        const element = await mountElement("cat1");

        const title = element.find(".card-title").element;
        const button = element.find("button[aria-label='Tool details']").element as HTMLButtonElement;
        const dialog = document.body.querySelector(".popover[role='dialog']");

        expect(button.previousElementSibling?.outerHTML).toBe("<b>Job</b>");
        expect(button.parentElement).toBe(title);
        expect(button.getAttribute("type")).toBe("button");
        expect(button.classList.value).toBe("g-link g-dark g-thin");
        expect(button.querySelector("svg")?.classList.value).toBe("svg-inline--fa fa-info-circle fa-sm");
        expect(button.getAttribute("aria-haspopup")).toBe("dialog");
        expect(button.getAttribute("aria-expanded")).toBe("false");
        expect(button.getAttribute("aria-controls")).toBe(dialog?.id);
        expect(dialog?.getAttribute("aria-label")).toBe("Tool");
        expect(button.nextElementSibling?.className).toBe("g-popover-host");
        expect(button.nextElementSibling?.nextElementSibling).toBeNull();
    });

    it("opens the tool dialog when the button gets keyboard focus", async () => {
        const element = await mountElement("cat1");
        const button = element.find("button[aria-label='Tool details']").element as HTMLButtonElement;

        button.focus();
        await nextTick();

        expect(button.getAttribute("aria-expanded")).toBe("true");
    });

    it("localizes the tool details button's accessible name", async () => {
        translations["Tool details"] = "Werkzeugdetails";

        const element = await mountElement("cat1");

        expect(element.find("button[aria-label='Werkzeugdetails']").exists()).toBe(true);
    });

    it("shows no tool details button or dialog until the job's tool is known", async () => {
        const element = await mountElement();

        expect(element.find("button[aria-label='Tool details']").exists()).toBe(false);
        expect(document.body.querySelector(".popover")).toBeNull();
    });
});
