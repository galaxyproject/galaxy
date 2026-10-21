import { createTestingPinia } from "@pinia/testing";
import { advanceTimersAndFlush, getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { JobState, ShowFullJobResponse } from "@/api/jobs";
import type { EntryPoint } from "@/stores/entryPointStore";

import ToolEntryPoints from "./ToolEntryPoints.vue";
import GCard from "@/components/Common/GCard.vue";

const { server, http } = useServerMock();

vi.useFakeTimers();

const JOB_ID = "job1";
const OTHER_JOB_ID = "job2";

function buildEntryPoint(overrides: Partial<EntryPoint> = {}): EntryPoint {
    return {
        model_class: "InteractiveToolEntryPoint",
        id: "ep1",
        job_id: JOB_ID,
        name: "Jupyter Interactive Tool",
        active: false,
        created_time: "2020-02-24T15:59:18.122103",
        modified_time: "2020-02-24T15:59:20.428594",
        output_datasets_ids: [],
        target: "http://ep1.interactivetoolentrypoint.interactivetool.localhost:8080/ipython/lab",
        ...overrides,
    };
}

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

let jobRequests = 0;

function mockJobState(state: JobState) {
    server.use(
        http.get("/api/jobs/{job_id}", ({ response }) => {
            jobRequests++;
            return response(200).json(buildJob(state));
        }),
    );
}

function mountWithEntryPoints(
    entryPoints: EntryPoint[],
    props: { job?: ShowFullJobResponse | null; otherJobsCount?: number } = {},
) {
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        stubActions: false,
        initialState: { entryPointStore: { entryPoints } },
    });
    const localVue = getLocalVue();

    return mount(ToolEntryPoints as object, {
        props: { jobId: JOB_ID, ...props },
        global: {
            ...withPlugins(localVue, pinia),
            stubs: { ...localVue.stubs, FontAwesomeIcon: true, RouterLink: true },
        },
    });
}

describe("ToolEntryPoints/ToolEntryPoints.vue", () => {
    enableAutoUnmount(afterEach);

    beforeEach(() => {
        jobRequests = 0;
        mockJobState("running");
    });

    afterEach(() => {
        vi.clearAllTimers();
    });

    it("shows a waiting state while the job has no entry points and is not terminal", async () => {
        const wrapper = mountWithEntryPoints([buildEntryPoint({ job_id: OTHER_JOB_ID })]);
        await advanceTimersAndFlush(0);

        const card = wrapper.findComponent(GCard);
        expect(jobRequests).toBeGreaterThan(0);
        expect(card.props("title")).toBe("Waiting for Interactive Tool session(s) to become available");
        expect(card.props("primaryActions")).toEqual([]);
        expect(card.props("badges")?.[0]?.label).toBe("0 active");
        expect(card.props("secondaryActions")?.[0]?.to).toBe("/interactivetool_entry_points/list");
        expect(wrapper.findAll('[data-description="entry point button"]').length).toBe(0);
    });

    it("shows a 'no sessions' state once the fetched job is terminal", async () => {
        mockJobState("ok");
        const wrapper = mountWithEntryPoints([buildEntryPoint({ job_id: OTHER_JOB_ID })]);
        await advanceTimersAndFlush(0);

        const card = wrapper.findComponent(GCard);
        expect(card.props("title")).toBe("No Interactive Tool sessions are currently available");
        expect(card.props("primaryActions")).toEqual([]);
    });

    it("uses a job passed by the parent instead of fetching it", async () => {
        const wrapper = mountWithEntryPoints([], { job: buildJob("ok") });
        await advanceTimersAndFlush(0);

        expect(jobRequests).toBe(0);
        expect(wrapper.findComponent(GCard).props("title")).toBe(
            "No Interactive Tool sessions are currently available",
        );
    });

    it("keeps waiting without fetching when the parent passes job=null", async () => {
        const wrapper = mountWithEntryPoints([], { job: null });
        await advanceTimersAndFlush(0);

        expect(jobRequests).toBe(0);
        expect(wrapper.findComponent(GCard).props("title")).toBe(
            "Waiting for Interactive Tool session(s) to become available",
        );
    });

    it("offers an open action for the job's single active entry point, ignoring other jobs' entry points", () => {
        const entryPoint = buildEntryPoint({ active: true });
        const wrapper = mountWithEntryPoints([
            entryPoint,
            buildEntryPoint({ id: "ep2", job_id: OTHER_JOB_ID, active: true, name: "Other job" }),
        ]);

        const card = wrapper.findComponent(GCard);
        expect(card.props("title")).toBe("There is an Interactive Tool session available");
        expect(card.props("badges")?.[0]?.label).toBe("1 active");

        const actions = card.props("primaryActions");
        expect(actions?.length).toBe(1);
        expect(actions![0]?.label).toBe("Open Jupyter Interactive Tool");

        const link = wrapper.find(`a[href='${entryPoint.target}']`);
        expect(link.attributes("target")).toBe("_blank");

        // A single entry point never renders the multi-entry grid.
        expect(wrapper.findAll('[data-description="entry point button"]').length).toBe(0);
    });

    it("shows a waiting-to-activate state with no open action when the single entry point is inactive", () => {
        const wrapper = mountWithEntryPoints([buildEntryPoint({ active: false })]);

        const card = wrapper.findComponent(GCard);
        expect(card.props("title")).toBe(
            "There is an Interactive Tool session available, waiting for it to become active",
        );
        expect(card.props("primaryActions")).toEqual([]);
        expect(card.props("badges")?.[0]?.label).toBe("0 active");
    });

    it("links each grid entry to its target in a new tab when all entry points are active", () => {
        const entryPoints = [
            buildEntryPoint({ id: "ep1", active: true }),
            buildEntryPoint({ id: "ep2", active: true, name: "AskOmics instance", target: "http://ep2.localhost/" }),
        ];
        const wrapper = mountWithEntryPoints(entryPoints);

        const card = wrapper.findComponent(GCard);
        expect(card.props("title")).toBe("There are multiple Interactive Tool sessions available");
        expect(card.props("badges")?.[0]?.label).toBe("2/2 active");
        expect(card.props("primaryActions")).toEqual([]);

        const buttons = wrapper.findAll('[data-description="entry point button"]');
        expect(buttons.map((button) => button.text())).toEqual(entryPoints.map((ep) => ep.name));
        expect(buttons.map((button) => button.attributes("href"))).toEqual(entryPoints.map((ep) => ep.target));
        buttons.forEach((button) => expect(button.attributes("target")).toBe("_blank"));

        expect(wrapper.text()).not.toContain("Some sessions are not active yet");
    });

    it("disables inactive grid entries and notes that some sessions are not active", () => {
        const entryPoints = [
            buildEntryPoint({ id: "ep1", active: true }),
            buildEntryPoint({ id: "ep2", active: false, name: "AskOmics instance" }),
        ];
        const wrapper = mountWithEntryPoints(entryPoints);

        expect(wrapper.findComponent(GCard).props("badges")?.[0]?.label).toBe("1/2 active");

        const [activeButton, inactiveButton] = wrapper.findAll('[data-description="entry point button"]');
        expect(activeButton?.attributes("href")).toBe(entryPoints[0]!.target);
        expect(inactiveButton?.attributes("href")).toBeUndefined();
        expect(inactiveButton?.attributes("aria-disabled")).toBe("true");

        expect(wrapper.text()).toContain("Some sessions are not active yet");
    });

    it.each([
        [undefined, null, null],
        [0, null, null],
        [
            1,
            "+1 job, paginate to view",
            "This run has 1 other job. Use the pagination above to view their Interactive Tools.",
        ],
        [
            3,
            "+3 jobs, paginate to view",
            "This run has 3 other jobs. Use the pagination above to view their Interactive Tools.",
        ],
    ])("shows the other jobs hint for otherJobsCount=%s", (otherJobsCount, expectedLabel, expectedTitle) => {
        const wrapper = mountWithEntryPoints([buildEntryPoint({ active: true })], { otherJobsCount });

        const hint = wrapper.find(".other-jobs-hint");
        if (expectedLabel === null) {
            expect(hint.exists()).toBe(false);
        } else {
            expect(hint.text()).toBe(expectedLabel);
            expect(hint.attributes("title")).toBe(expectedTitle);
        }
    });
});
