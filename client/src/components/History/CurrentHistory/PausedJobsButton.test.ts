import { getFakeHistorySummary, getFakeQuotaUsageData, getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type { AnyUser, HistorySummary, HistorySummaryExtended } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { toQuotaUsage } from "@/components/User/DiskUsage/Quota/model/QuotaUsage";
import { useHistoryStore } from "@/stores/historyStore";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";

import PausedJobsButton from "./PausedJobsButton.vue";

enableAutoUnmount(afterEach);

const localVue = getLocalVue();
const { server, http } = useServerMock();

const BUTTON = "[data-description='paused jobs button']";
const RESUME = "[data-description='resume paused jobs button']";
const SHOW_PAUSED = "[data-description='show paused jobs']";
const OVER_QUOTA_NOTE = "[data-description='paused jobs over quota']";

const OWNER = getFakeRegisteredUser({ quota_percent: 50 });

let requested: string[];

beforeEach(() => {
    requested = [];
    server.use(
        http.put("/api/histories/{history_id}/resume_paused_jobs", ({ params, response }) => {
            requested.push(`resume ${params.history_id}`);
            return response(204).empty();
        }),
        http.get("/api/histories/{history_id}", ({ params, response }) => {
            requested.push(`stats ${params.history_id}`);
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return response(200).json({ paused_jobs_count: 0 } as any);
        }),
    );
});

afterEach(() => {
    document.body.innerHTML = "";
});

/** The user's history with 2 paused jobs, as the history store holds it. */
function getPausedHistory(data: Partial<HistorySummary> = {}) {
    return { ...getFakeHistorySummary(data), paused_jobs_count: 2 };
}

async function mountButton(
    history: HistorySummary & Pick<HistorySummaryExtended, "paused_jobs_count"> = getPausedHistory(),
    currentUser: AnyUser = OWNER,
    otherSourcesUsage = 0,
) {
    const pinia = createPinia();
    setActivePinia(pinia);
    if (otherSourcesUsage) {
        useQuotaUsageStore().quotaUsages = [toQuotaUsage(getFakeQuotaUsageData("scratch", otherSourcesUsage))];
    }
    // The panel passes the stored history, which the store updates in place
    const historyStore = useHistoryStore();
    historyStore.setHistory(history);
    const wrapper = mount(PausedJobsButton, {
        attachTo: document.body,
        props: { history: historyStore.getHistoryById(history.id)!, currentUser },
        global: withPlugins(localVue, pinia),
    });
    await flushPromises();
    return wrapper;
}

async function openPopover(wrapper: VueWrapper) {
    await wrapper.find(BUTTON).trigger("click");
    await nextTick();
}

/** Finds an element of the popover, which moves out of the wrapper into the document. */
function popoverElement(selector: string) {
    const element = document.body.querySelector<HTMLElement>(selector);
    if (!element) {
        throw new Error(`${selector} not found in the popover`);
    }
    return element;
}

describe("PausedJobsButton", () => {
    it("shows how many jobs are paused in the user's history", async () => {
        const wrapper = await mountButton();

        expect(wrapper.find(BUTTON).text()).toBe("2");
        expect(wrapper.find(BUTTON).attributes("aria-label")).toBe("Paused jobs (2)");
    });

    it.each([
        ["no jobs are paused", { ...getFakeHistorySummary(), paused_jobs_count: 0 }],
        ["the history doesn't say", getFakeHistorySummary()],
    ])("shows nothing when %s", async (_description, history) => {
        const wrapper = await mountButton(history);

        expect(wrapper.find(BUTTON).exists()).toBe(false);
    });

    it.each([
        ["another user's history", { ...getPausedHistory(), user_id: "other_user_id" }],
        ["an archived history", getPausedHistory({ archived: true })],
        ["a purged history", getPausedHistory({ purged: true })],
    ])("doesn't offer to resume the paused jobs of %s", async (_description, history) => {
        const wrapper = await mountButton(history);

        expect(wrapper.find(BUTTON).exists()).toBe(false);
    });

    it("resumes the paused jobs of the history and hides itself once the history has none", async () => {
        const wrapper = await mountButton();
        await openPopover(wrapper);

        popoverElement(RESUME).click();
        await flushPromises();

        expect(requested).toEqual(["resume fake_history_id", "stats fake_history_id"]);
        expect(wrapper.find(BUTTON).exists()).toBe(false);
    });

    it.each([
        ["the default storage", getFakeRegisteredUser({ quota_percent: 100 }), 0],
        ["another storage", OWNER, 1001],
    ])("doesn't let the user resume while over the quota of %s", async (_description, user, otherSourcesUsage) => {
        const wrapper = await mountButton(getPausedHistory(), user, otherSourcesUsage);
        await openPopover(wrapper);

        popoverElement(RESUME).click();
        await flushPromises();

        expect(popoverElement(RESUME).getAttribute("aria-disabled")).toBe("true");
        expect(requested).not.toContain("resume fake_history_id");
        expect(popoverElement(OVER_QUOTA_NOTE).textContent?.trim()).toBe(
            "You are over your disk quota. Free some space to resume them.",
        );
    });

    it("asks to show the paused jobs", async () => {
        const wrapper = await mountButton();
        await openPopover(wrapper);

        popoverElement(SHOW_PAUSED).click();
        await nextTick();

        expect(wrapper.emitted("show-paused")).toEqual([[]]);
    });
});
