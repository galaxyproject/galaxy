import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { ShowFullJobResponse } from "@/api/jobs";
import { MAX_CACHED_JOBS, useJobStore } from "@/stores/jobStore";
import { type Tool, useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import JobPanel from "./JobPanel.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import JobStatusFilter from "@/components/Jobs/JobStatusFilter.vue";
import JobTimeRangeFilter from "@/components/Jobs/JobTimeRangeFilter.vue";

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
    /** Created to ensure each wrapper is properly unmounted after each test. */
    let activeWrapper: VueWrapper | null = null;

    afterEach(() => {
        activeWrapper?.unmount();
        activeWrapper = null;
    });

    /** Mounts `JobPanel` against a fresh store/user, so each test gets its own isolated state
     * instead of sharing one `beforeEach`-mounted instance. `getLocalVue()` creates and activates
     * its own Pinia instance, so it must run before `useUserStore()` below -- otherwise the store
     * it sets state on isn't the one `mount()` ends up using. */
    function mountJobPanel({ showToolNames = false } = {}): VueWrapper {
        const localVue = getLocalVue();
        const userStore = useUserStore();
        userStore.currentUser = getFakeRegisteredUser({ id: "fakeUser", email: "fake_user_email" });
        userStore.showToolNamesInJobPanel = showToolNames;
        activeWrapper = mount(JobPanel as object, { localVue, router });
        return activeWrapper;
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

    it("pages by create_time and excludes hidden-tool jobs server-side", async () => {
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

        // `create_time`: a job can't skip past the offset when it changes state mid-scroll.
        expect(requests.at(-1)?.get("order_by")).toBe("create_time");
        // `exclude_tool_ids`: hidden-tool jobs are excluded server-side, not fetched and dropped.
        expect(requests.at(-1)?.getAll("exclude_tool_ids")).toEqual(["__DATA_FETCH__", "upload1"]);
    });

    it("sets and clears the status quick-filter via JobStatusFilter", async () => {
        const requests: URLSearchParams[] = [];
        server.use(
            http.get("/api/jobs", ({ request, response }) => {
                requests.push(new URL(request.url).searchParams);
                return response(200).json([], { headers: { total_matches: "0" } });
            }),
        );

        const wrapper = mountJobPanel();
        await flushPromises();

        wrapper.findComponent(JobStatusFilter).vm.$emit("update:active-group", "problem");
        await flushPromises();
        await scrollOnce();

        expect(requests.at(-1)?.getAll("state")).toEqual(["error", "failed"]);

        // Clicking the same group again toggles it off.
        wrapper.findComponent(JobStatusFilter).vm.$emit("update:active-group", undefined);
        await flushPromises();
        await scrollOnce();

        expect(requests.at(-1)?.has("state")).toBe(false);
    });

    it("clears a manually-picked state's stale text when a quick-filter group is toggled on", async () => {
        server.use(
            http.get("/api/jobs", ({ response }) => {
                return response(200).json([], { headers: { total_matches: "0" } });
            }),
        );

        const wrapper = mountJobPanel();
        await flushPromises();
        wrapper.findComponent(FilterMenu).vm.$emit("update:filterText", "state:ok");
        await flushPromises();

        expect(wrapper.findComponent(FilterMenu).props("filterText")).toBe("state:ok");

        wrapper.findComponent(JobStatusFilter).vm.$emit("update:active-group", "active");
        await flushPromises();

        // The stale `state:ok` text is removed, not just overridden -- jobsFilterParams already
        // prefers status over state regardless, so this is about the visible text, not params.
        const filterText = wrapper.findComponent(FilterMenu).props("filterText") as string;
        expect(filterText).not.toContain("state:ok");
        expect(filterText).toContain("status:active");
    });

    it("sets and clears the time-range quick-filter via JobTimeRangeFilter", async () => {
        vi.useFakeTimers();
        try {
            vi.setSystemTime(new Date("2024-01-01T12:00:00.000Z"));
            const requests: URLSearchParams[] = [];
            server.use(
                http.get("/api/jobs", ({ request, response }) => {
                    requests.push(new URL(request.url).searchParams);
                    return response(200).json([], { headers: { total_matches: "0" } });
                }),
            );

            const wrapper = mountJobPanel();
            await flushPromises();

            wrapper.findComponent(JobTimeRangeFilter).vm.$emit("update:active-range", "1h");
            await flushPromises();
            await scrollOnce();

            expect(requests.at(-1)?.get("date_range_min")).toBe("2024-01-01t11:00:00.000z");

            wrapper.findComponent(JobTimeRangeFilter).vm.$emit("update:active-range", undefined);
            await flushPromises();
            await scrollOnce();

            expect(requests.at(-1)?.has("date_range_min")).toBe(false);
        } finally {
            vi.useRealTimers();
        }
    });

    it("shows a manually-entered update_time filter as the 'custom' range, not a quick-pick one", async () => {
        server.use(
            http.get("/api/jobs", ({ response }) => {
                return response(200).json([], { headers: { total_matches: "0" } });
            }),
        );

        const wrapper = mountJobPanel();
        await flushPromises();

        expect(wrapper.findComponent(JobTimeRangeFilter).props("activeRange")).toBeUndefined();

        wrapper.findComponent(FilterMenu).vm.$emit("update:filterText", "update_time>2024-01-01T00:00:00");
        await flushPromises();

        expect(wrapper.findComponent(JobTimeRangeFilter).props("activeRange")).toBe("custom");
    });

    it("stops retrying once an exhausted page is entirely rejected by the client matcher", async () => {
        const requests: URLSearchParams[] = [];
        server.use(
            http.get("/api/jobs", ({ request, response }) => {
                requests.push(new URL(request.url).searchParams);
                // The server claims 3 jobs match `state:ok` but actually returns jobs in a
                // different state (e.g. a server/client filter disagreement). The client
                // matcher correctly rejects all of them.
                const jobs = [
                    buildJob({ id: "job1", state: "error" }),
                    buildJob({ id: "job2", state: "error" }),
                    buildJob({ id: "job3", state: "error" }),
                ];
                return response(200).json(jobs, { headers: { total_matches: "3" } });
            }),
        );

        const wrapper = mountJobPanel();
        await flushPromises();
        wrapper.findComponent(FilterMenu).vm.$emit("update:filterText", "state:ok");
        await flushPromises();
        await scrollOnce();
        await flushPromises();

        expect(wrapper.text()).toContain("No jobs found");

        const requestCountAfterSettling = requests.length;
        await scrollOnce();
        await flushPromises();

        // The page has been exhausted and all jobs were rejected by the client matcher,
        // so no further requests should be made for this page.
        expect(requests.length).toBe(requestCountAfterSettling);
    });

    it("only requests the total count on the first page, keeping it stable on later pages", async () => {
        /** Tracks the values of the `include_total_count` query parameter for each request. */
        const includeTotalCountValues: (string | null)[] = [];
        server.use(
            http.get("/api/jobs", ({ request, response }) => {
                const url = new URL(request.url);
                includeTotalCountValues.push(url.searchParams.get("include_total_count"));
                const offset = Number(url.searchParams.get("offset") ?? "0");
                const jobs = offset === 0 ? [buildJob({ id: "job1" })] : [buildJob({ id: "job2" })];
                return response(200).json(jobs, offset === 0 ? { headers: { total_matches: "2" } } : {});
            }),
        );

        const wrapper = mountJobPanel();
        await flushPromises();
        await scrollOnce(); // completes the first page
        await scrollOnce(); // triggers and completes the second page

        expect(includeTotalCountValues).toEqual(["true", "false"]);
        expect(wrapper.text()).toContain("All jobs loaded");
    });

    it("includes upload jobs once the Include Uploads toggle is switched on", async () => {
        server.use(
            http.get("/api/jobs", ({ request, response }) => {
                const excludesUploads = new URL(request.url).searchParams.getAll("exclude_tool_ids").length > 0;
                const jobs = excludesUploads ? [] : [buildJob({ id: "uploadJob", tool_id: "__DATA_FETCH__" })];
                return response(200).json(jobs, { headers: { total_matches: `${jobs.length}` } });
            }),
        );

        const wrapper = mountJobPanel();
        await flushPromises();
        await scrollOnce();

        expect(wrapper.find("#g-card-job-uploadJob").exists()).toBe(false);

        await wrapper.find('[data-test-id="job-panel-include-uploads-toggle"]').setValue(true);
        await flushPromises();
        await scrollOnce();

        expect(wrapper.find("#g-card-job-uploadJob").exists()).toBe(true);
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

    it("picks up a new job matching the active filter via periodic re-check", async () => {
        vi.useFakeTimers();
        try {
            let newJobVisible = false;
            server.use(
                http.get("/api/jobs", ({ response }) => {
                    const jobs = newJobVisible ? [buildJob({ id: "newJob", state: "queued" })] : [];
                    return response(200).json(jobs, { headers: { total_matches: `${jobs.length}` } });
                }),
            );

            const wrapper = mountJobPanel();
            await flushPromises();
            wrapper.findComponent(FilterMenu).vm.$emit("update:filterText", "state:queued");
            await flushPromises();

            expect(wrapper.find("#g-card-job-newJob").exists()).toBe(false);

            // The job starts matching the filter sometime after the panel's initial fetch.
            newJobVisible = true;
            await vi.advanceTimersByTimeAsync(3000);
            await flushPromises();

            expect(wrapper.find("#g-card-job-newJob").exists()).toBe(true);
        } finally {
            vi.useRealTimers();
        }
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

    it("keeps the spinner on for a still-in-flight request even if an older, discarded one resolves first", async () => {
        let resolveOld: (() => void) | undefined;
        let resolveNew: (() => void) | undefined;
        server.use(
            http.get("/api/jobs", async ({ request, response }) => {
                const isNewFilter = new URL(request.url).searchParams.get("search") === "tool:cat1";
                await new Promise<void>((resolve) => {
                    if (isNewFilter) {
                        resolveNew = resolve;
                    } else {
                        resolveOld = resolve;
                    }
                });
                return response(200).json([], { headers: { total_matches: "0" } });
            }),
        );

        const wrapper = mountJobPanel();
        await flushPromises();
        loadMore?.();
        await flushPromises();
        // The initial (soon-to-be-discarded) fetch is now in flight.

        wrapper.findComponent(FilterMenu).vm.$emit("update:filterText", "tool_id:cat1");
        await flushPromises();
        loadMore?.(); // now bound to the remounted ScrollList for the new filter
        await flushPromises();
        // The new filter's own fetch is now also in flight; both requests are pending.

        expect(wrapper.findComponent(FilterMenu).props("loading")).toBe(true);

        resolveOld?.();
        await flushPromises();

        // The old, discarded request resolving must not clear the spinner for the still-pending new one.
        expect(wrapper.findComponent(FilterMenu).props("loading")).toBe(true);

        resolveNew?.();
        await flushPromises();

        expect(wrapper.findComponent(FilterMenu).props("loading")).toBe(false);
    });

    it("doesn't leave the spinner stuck if typing an invalid filter fails before a prior request resolves", async () => {
        let resolveOld: (() => void) | undefined;
        server.use(
            http.get("/api/jobs", async ({ response }) => {
                await new Promise<void>((resolve) => {
                    resolveOld = resolve;
                });
                return response(200).json([], { headers: { total_matches: "0" } });
            }),
        );

        const wrapper = mountJobPanel();
        await flushPromises();
        loadMore?.();
        await flushPromises();

        expect(wrapper.findComponent(FilterMenu).props("loading")).toBe(true);

        wrapper.findComponent(FilterMenu).vm.$emit("update:filterText", "xx:ss");
        await flushPromises();
        loadMore?.(); // now bound to the remounted ScrollList for the invalid filter
        await flushPromises();

        resolveOld?.();
        await flushPromises();

        expect(wrapper.findComponent(FilterMenu).props("loading")).toBe(false);
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
