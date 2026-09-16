import { createTestingPinia } from "@pinia/testing";
import { advanceTimersAndFlush, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { PiniaVuePlugin, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { JobState, ShowFullJobResponse } from "@/api/jobs";
import type { EntryPoint } from "@/stores/entryPointStore";

import ToolEntryPoints from "./ToolEntryPoints.vue";
import GCard from "@/components/Common/GCard.vue";

const { server, http } = useServerMock();

vi.useFakeTimers();

function buildEntryPoint(overrides: Partial<EntryPoint> = {}): EntryPoint {
    return {
        model_class: "InteractiveToolEntryPoint",
        id: "ep1",
        job_id: "job1",
        name: "Jupyter Interactive Tool",
        active: false,
        created_time: "2020-02-24T15:59:18.122103",
        modified_time: "2020-02-24T15:59:20.428594",
        target: "http://ep1.interactivetoolentrypoint.interactivetool.localhost:8080/ipython/lab",
        ...overrides,
    } as EntryPoint;
}

const JOB_ID = "job1";
const OTHER_JOB_ID = "job2";

function buildJob(state: JobState): ShowFullJobResponse {
    return {
        id: JOB_ID,
        state,
        model_class: "Job",
        create_time: "2024-01-01T00:00:00",
        update_time: "2024-01-01T00:00:00",
        inputs: {},
        outputs: {},
        output_collections: {},
        params: {},
        tool_id: "cat1",
    } as ShowFullJobResponse;
}

function mockJobState(state: JobState) {
    server.use(
        http.get("/api/jobs/{job_id}", ({ response }) => {
            return response(200).json(buildJob(state));
        }),
    );
}

function mountWithEntryPoints(entryPoints: EntryPoint[], jobId = JOB_ID) {
    const testPinia = createTestingPinia({
        createSpy: vi.fn,
        stubActions: false,
        initialState: {
            entryPointStore: {
                entryPoints,
            },
        },
    });
    setActivePinia(testPinia);

    const localVue = getLocalVue();
    localVue.use(PiniaVuePlugin);

    return mount(ToolEntryPoints as object, {
        propsData: {
            jobId,
        },
        localVue,
        pinia: testPinia,
        stubs: {
            FontAwesomeIcon: true,
        },
    });
}

describe("ToolEntryPoints/ToolEntryPoints.vue", () => {
    beforeEach(() => {
        mockJobState("running");
    });

    afterEach(() => {
        vi.clearAllTimers();
    });

    it("shows a waiting state and no primary action when there are no entry points and the job is not terminal", async () => {
        mockJobState("running");
        const wrapper = mountWithEntryPoints([buildEntryPoint({ job_id: OTHER_JOB_ID })]);
        await advanceTimersAndFlush(0);

        const card = wrapper.findComponent(GCard);
        expect(card.props("title")).toBe("Waiting for Interactive Tool session(s) to become available");
        expect(card.props("primaryActions")).toEqual([]);
        expect(card.props("badges")?.[0]?.label).toBe("0 active");
        expect(wrapper.findAll('[data-description="entry point button"]').length).toBe(0);
    });

    it("shows a 'no sessions' state when there are no entry points and the job has reached a terminal state", async () => {
        mockJobState("ok");
        const wrapper = mountWithEntryPoints([buildEntryPoint({ job_id: OTHER_JOB_ID })]);
        await advanceTimersAndFlush(0);

        const card = wrapper.findComponent(GCard);
        expect(card.props("title")).toBe("No Interactive Tool sessions are currently available");
        expect(card.props("primaryActions")).toEqual([]);
    });

    it("shows an active state with an open link when there is a single active entry point", () => {
        const entryPoint = buildEntryPoint({ active: true, name: "Jupyter Interactive Tool" });
        const wrapper = mountWithEntryPoints([entryPoint]);

        const card = wrapper.findComponent(GCard);
        expect(card.props("title")).toBe("There is an Interactive Tool session available");
        expect(card.props("badges")?.[0]?.label).toBe("1 active");

        const actions = card.props("primaryActions");
        expect(actions.length).toBe(1);
        expect(actions[0].label).toBe("Open Jupyter Interactive Tool");
        expect(actions[0].href).toBe(entryPoint.target);

        // Single entry point never renders the multi-entry grid.
        expect(wrapper.findAll('[data-description="entry point button"]').length).toBe(0);
    });

    it("shows a waiting-to-activate state with no primary action when the single entry point is inactive", () => {
        const wrapper = mountWithEntryPoints([buildEntryPoint({ active: false })]);

        const card = wrapper.findComponent(GCard);
        expect(card.props("title")).toBe(
            "There is an Interactive Tool session available, waiting for it to become active",
        );
        expect(card.props("primaryActions")).toEqual([]);
        expect(card.props("badges")?.[0]?.label).toBe("0 active");
    });

    it("renders a grid entry for each entry point when there are multiple, all active", () => {
        const entryPoints = [
            buildEntryPoint({ id: "ep1", active: true, name: "Jupyter Interactive Tool" }),
            buildEntryPoint({ id: "ep2", active: true, name: "AskOmics instance" }),
        ];
        const wrapper = mountWithEntryPoints(entryPoints);

        const card = wrapper.findComponent(GCard);
        expect(card.props("title")).toBe("There are multiple Interactive Tool sessions available");
        expect(card.props("badges")?.[0]?.label).toBe("2/2 active");
        // No single-entry-point shortcut action when there's more than one.
        expect(card.props("primaryActions")).toEqual([]);

        const buttons = wrapper.findAll('[data-description="entry point button"]');
        expect(buttons.length).toBe(2);
        buttons.wrappers.forEach((button) => {
            expect(button.attributes("href")).toBeTruthy();
        });

        // All active, so the "some sessions not active" note should not render.
        expect(wrapper.text()).not.toContain("Some sessions are not active yet");
    });

    it("renders disabled grid entries and a note when some entry points are inactive", () => {
        const entryPoints = [
            buildEntryPoint({ id: "ep1", active: true, name: "Jupyter Interactive Tool" }),
            buildEntryPoint({ id: "ep2", active: false, name: "AskOmics instance" }),
        ];
        const wrapper = mountWithEntryPoints(entryPoints);

        const card = wrapper.findComponent(GCard);
        expect(card.props("badges")?.[0]?.label).toBe("1/2 active");

        const buttons = wrapper.findAll('[data-description="entry point button"]');
        expect(buttons.length).toBe(2);

        const activeButton = buttons.wrappers.find((button) => button.text().includes("Jupyter"));
        const inactiveButton = buttons.wrappers.find((button) => button.text().includes("AskOmics"));

        expect(activeButton?.attributes("href")).toBeTruthy();
        expect(inactiveButton?.attributes("aria-disabled")).toBe("true");

        expect(wrapper.text()).toContain("Some sessions are not active yet");
    });

    it("only counts entry points belonging to the given jobId", () => {
        const entryPoints = [
            buildEntryPoint({ id: "ep1", job_id: JOB_ID, active: true, name: "This job" }),
            buildEntryPoint({ id: "ep2", job_id: OTHER_JOB_ID, active: true, name: "Other job" }),
        ];
        const wrapper = mountWithEntryPoints(entryPoints, JOB_ID);

        const card = wrapper.findComponent(GCard);
        expect(card.props("title")).toBe("There is an Interactive Tool session available");
        expect(card.props("badges")?.[0]?.label).toBe("1 active");
    });
});
