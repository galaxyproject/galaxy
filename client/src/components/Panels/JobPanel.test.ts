import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { ShowFullJobResponse } from "@/api/jobs";
import { MAX_CACHED_JOBS, useJobStore } from "@/stores/jobStore";
import { type Tool, useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import JobPanel from "./JobPanel.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";

const { server, http } = useServerMock();

const router = injectTestRouter(getLocalVue());

// Default handler for tests that don't care about pagination; the scroll-cap test below
// overrides it with its own, since the most recently registered handler wins.
server.use(
    http.get("/api/jobs", ({ response }) => {
        return response(200).json([]);
    }),
);

/** The infinite scroll callback `ScrollList` registers on mount, captured so tests can
 * trigger additional pages without a real scroll event (same technique as ScrollList.test.ts). */
let loadMore: (() => void) | null = null;

vi.mock("@vueuse/core", async () => ({
    ...(await vi.importActual("@vueuse/core")),
    useInfiniteScroll: vi.fn((_element, callback) => {
        loadMore = callback;
        return {};
    }),
}));

/** Mocks a single scroll-to-bottom event that triggers `ScrollList` to load its next page. */
async function scrollOnce() {
    loadMore?.();
    await flushPromises();
}

function buildJob(overrides: Partial<ShowFullJobResponse> = {}): ShowFullJobResponse {
    return {
        id: "job1",
        state: "ok",
        model_class: "Job",
        create_time: "2024-01-01T00:00:00",
        update_time: "2024-01-01T00:00:00",
        inputs: {},
        outputs: {},
        output_collections: {},
        params: {},
        tool_id: "cat1",
        ...overrides,
    } as ShowFullJobResponse;
}

describe("JobPanel", () => {
    /** Mounts `JobPanel` against a fresh store/user, so each test gets its own isolated state
     * instead of sharing one `beforeEach`-mounted instance. `getLocalVue()` creates and activates
     * its own Pinia instance, so it must run before `useUserStore()` below -- otherwise the store
     * it sets state on isn't the one `mount()` ends up using. */
    function mountJobPanel({ showToolNames = false } = {}): VueWrapper {
        const localVue = getLocalVue();
        const userStore = useUserStore();
        userStore.currentUser = getFakeRegisteredUser({ id: "fakeUser", email: "fake_user_email" });
        userStore.showToolNamesInJobPanel = showToolNames;
        return mount(JobPanel as object, { localVue, router });
    }

    it("shows a job that lands in jobStore via another view while no filter is active", async () => {
        const wrapper = mountJobPanel();
        await flushPromises();

        const jobStore = useJobStore();
        jobStore.updateJob("job1", buildJob());
        await flushPromises();

        expect(wrapper.text()).toContain("cat1");
    });

    it("does not show a job belonging to another user (by user_id)", async () => {
        const wrapper = mountJobPanel();
        await flushPromises();

        const jobStore = useJobStore();
        jobStore.updateJob("job1", buildJob({ user_id: "otherUser" }));
        await flushPromises();

        expect(wrapper.text()).not.toContain("cat1");
    });

    it("does not show a job belonging to another user (by user_email)", async () => {
        const wrapper = mountJobPanel();
        await flushPromises();

        const jobStore = useJobStore();
        jobStore.updateJob("job1", buildJob({ user_email: "someone_else@example.com" }));
        await flushPromises();

        expect(wrapper.text()).not.toContain("cat1");
    });

    it("shows a job with no owner information (the common, non-admin case)", async () => {
        const wrapper = mountJobPanel();
        await flushPromises();

        const jobStore = useJobStore();
        jobStore.updateJob("job1", buildJob({ user_id: null, user_email: null }));
        await flushPromises();

        expect(wrapper.text()).toContain("cat1");
    });

    it.each(["running", "finishing"] as const)("updates the state of a listed %s job", async (state) => {
        server.use(
            http.get("/api/jobs", ({ request, response }) => {
                /** Is a poll for active/non-terminal jobs */
                const isActivePoll = new URL(request.url).searchParams.has("job_id");
                return response(200).json([buildJob({ id: "activeJob", state: isActivePoll ? "ok" : state })], {
                    headers: { total_matches: "1" },
                });
            }),
        );

        const wrapper = mountJobPanel();
        await flushPromises();
        await scrollOnce();

        expect(wrapper.find("#g-card-job-activeJob .job-state-badge").text()).toContain("ok");
    });

    it("polls all active jobs in one batched request instead of one per card", async () => {
        const singleJobRequests: string[] = [];
        const activePollRequests: string[][] = [];
        server.use(
            http.get("/api/jobs/{job_id}", ({ params, response }) => {
                singleJobRequests.push(params.job_id as string);
                return response(200).json(buildJob({ id: params.job_id as string, state: "ok" }));
            }),
            http.get("/api/jobs", ({ request, response }) => {
                const jobIds = new URL(request.url).searchParams.getAll("job_id");
                if (jobIds.length > 0) {
                    activePollRequests.push(jobIds);
                    return response(200).json(
                        jobIds.map((id) => buildJob({ id, state: "ok" })),
                        { headers: { total_matches: `${jobIds.length}` } },
                    );
                }
                return response(200).json(
                    [buildJob({ id: "job1", state: "running" }), buildJob({ id: "job2", state: "running" })],
                    { headers: { total_matches: "2" } },
                );
            }),
        );

        mountJobPanel();
        await flushPromises();
        await scrollOnce();

        // There were no individual job requests because all active jobs were polled in a single batched request.
        expect(singleJobRequests).toEqual([]);
        expect(activePollRequests[0]?.sort()).toEqual(["job1", "job2"]);
    });

    it("refetches in name mode when the name toggle flips with filter text present", async () => {
        const requests: URLSearchParams[] = [];
        server.use(
            http.get("/api/jobs", ({ request, response }) => {
                requests.push(new URL(request.url).searchParams);
                return response(200).json([], { headers: { total_matches: "0" } });
            }),
        );

        const wrapper = mountJobPanel();
        useToolStore().saveAllTools([{ id: "cat1", name: "Concatenate datasets" }] as unknown as Tool[]);
        await flushPromises();
        wrapper.findComponent(FilterMenu).vm.$emit("update:filterText", "concat");
        await flushPromises();
        await scrollOnce();
        expect(requests.at(-1)?.get("search")).toBe("tool:concat");

        useUserStore().showToolNamesInJobPanel = true;
        await flushPromises();
        await scrollOnce();

        expect(requests.at(-1)?.getAll("tool_id")).toEqual(["cat1"]);
    });

    it("pages by create_time, not update_time, so a job can't skip past the offset when it changes state", async () => {
        const requests: URLSearchParams[] = [];
        server.use(
            http.get("/api/jobs", ({ request, response }) => {
                requests.push(new URL(request.url).searchParams);
                return response(200).json([], { headers: { total_matches: "0" } });
            }),
        );

        mountJobPanel();
        await flushPromises();
        await scrollOnce();

        expect(requests.at(-1)?.get("order_by")).toBe("create_time");
    });

    it("loads the tool store to search and title jobs by tool name", async () => {
        const requests: URLSearchParams[] = [];
        server.use(
            http.untyped.get("/api/tools", () => {
                return HttpResponse.json([{ id: "cat1", name: "Concatenate datasets" }]);
            }),
            http.get("/api/jobs", ({ request, response }) => {
                requests.push(new URL(request.url).searchParams);
                return response(200).json(
                    [buildJob({ id: "catJob" }), buildJob({ id: "goneJob", tool_id: "uninstalled_tool" })],
                    { headers: { total_matches: "2" } },
                );
            }),
        );

        const wrapper = mountJobPanel({ showToolNames: true });
        await flushPromises();
        wrapper.findComponent(FilterMenu).vm.$emit("update:filterText", "concat");
        await flushPromises();
        await scrollOnce();

        expect(requests.at(-1)?.getAll("tool_id")).toEqual(["cat1"]);
        expect(wrapper.find("#g-card-job-catJob .job-card-title-text").text()).toBe("Concatenate datasets");
        expect(wrapper.find("#g-card-job-goneJob .job-card-title-text").text()).toBe("uninstalled_tool");
    });

    it("hides a job once a live update takes it out of the active filter's criteria", async () => {
        server.use(
            http.get("/api/jobs", ({ response }) => {
                return response(200).json([buildJob({ id: "job1", state: "queued" })], {
                    headers: { total_matches: "1" },
                });
            }),
        );

        const wrapper = mountJobPanel();
        await flushPromises();
        wrapper.findComponent(FilterMenu).vm.$emit("update:filterText", "state:queued");
        await flushPromises();
        await scrollOnce();

        expect(wrapper.find("#g-card-job-job1").exists()).toBe(true);

        // Simulate the job reaching a terminal state while the panel is still showing it
        // (e.g. via JobState's own polling), same as a real state change would.
        useJobStore().updateJob("job1", buildJob({ id: "job1", state: "ok" }));
        await flushPromises();

        expect(wrapper.find("#g-card-job-job1").exists()).toBe(false);
    });

    it("shows an invalid filter error with a clear-search hint", async () => {
        const wrapper = mountJobPanel();
        await flushPromises();
        wrapper.findComponent(FilterMenu).vm.$emit("update:filterText", "xx:ss");
        await flushPromises();
        await scrollOnce();

        const alert = wrapper.find(".alert-danger");
        expect(alert.text()).toContain("Invalid filter(s) in query: xx");
        expect(alert.text()).toContain("Clear your search or click the button at the bottom of the list to retry.");
    });

    it("drops a page that resolves after the filter changed", async () => {
        let releaseStalePage: () => void = () => {};
        const stalePage = new Promise<void>((resolve) => {
            releaseStalePage = resolve;
        });
        server.use(
            http.get("/api/jobs", async ({ request, response }) => {
                if (new URL(request.url).searchParams.get("search") === "tool:cat1") {
                    return response(200).json([], { headers: { total_matches: "0" } });
                }
                await stalePage;
                return response(200).json([buildJob({ id: "staleJob", tool_id: "random_lines1" })], {
                    headers: { total_matches: "1" },
                });
            }),
        );

        const wrapper = mountJobPanel();
        await flushPromises();
        loadMore?.();
        wrapper.findComponent(FilterMenu).vm.$emit("update:filterText", "tool_id:cat1");
        await flushPromises();
        await scrollOnce();
        releaseStalePage();
        await flushPromises();

        expect(wrapper.find("#g-card-job-staleJob").exists()).toBe(false);
    });

    it("keeps showing more jobs once scrolling has loaded past jobStore's cache cap", async () => {
        // Pages through a pool larger than MAX_CACHED_JOBS, so later pages' `updateJob` calls
        // would evict earlier pages' jobs from the store if the panel didn't retain them
        // (see `addCurrentJob`).
        const PAGE_SIZE = 20;
        const TOTAL_JOBS = MAX_CACHED_JOBS + PAGE_SIZE;
        server.use(
            http.get("/api/jobs", ({ request, response }) => {
                const url = new URL(request.url);
                const offset = Number(url.searchParams.get("offset") ?? "0");
                const limit = Number(url.searchParams.get("limit") ?? `${PAGE_SIZE}`);
                const jobs = Array.from({ length: Math.min(limit, TOTAL_JOBS - offset) }, (_, i) =>
                    buildJob({
                        id: `job${offset + i}`,
                        update_time: new Date(Date.UTC(2024, 0, 1) - (offset + i) * 60_000).toISOString(),
                    }),
                );
                return response(200).json(jobs, { headers: { total_matches: `${TOTAL_JOBS}` } });
            }),
        );

        const wrapper = mountJobPanel();
        await flushPromises();

        // Scroll enough times to load every job in the pool.
        for (let i = 0; i < TOTAL_JOBS / PAGE_SIZE; i++) {
            await scrollOnce();
        }

        expect(wrapper.text()).toContain("All jobs loaded");
        const cardIds = wrapper.findAll(".g-card").map((card) => card.attributes("id"));
        expect(cardIds.length).toBe(TOTAL_JOBS);
        expect(cardIds[0]).toBe("g-card-job-job0");
        expect(cardIds.at(-1)).toBe(`g-card-job-job${TOTAL_JOBS - 1}`);
    });
});
