import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { BroadcastNotification } from "@/stores/broadcastsStore";

import { generateNewBroadcast } from "./test.utils";

import BroadcastsList from "./BroadcastsList.vue";
import Heading from "@/components/Common/Heading.vue";

const localVue = getLocalVue(true);

const selectors = {
    emptyBroadcastsListAlert: "#empty-broadcast-list-alert",
    broadcastItem: "[data-test-id='broadcast-item']",
} as const;

const filterButtons = {
    active: "#show-active-filter-button",
    scheduled: "#show-scheduled-filter-button",
    expired: "#show-expired-filter-button",
} as const;

type Filter = keyof typeof filterButtons;

const NOW = new Date("2026-10-10T12:00:00Z").getTime();

const { server, http } = useServerMock();

beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(NOW);
});

afterEach(() => {
    vi.useRealTimers();
});

/** A broadcast titled `subject`, published and expiring at the given offsets (ms) from now. */
function broadcastBetween(subject: string, publishedOffset: number, expiresOffset: number): BroadcastNotification {
    const broadcast = generateNewBroadcast({});
    return {
        ...broadcast,
        publication_time: new Date(NOW + publishedOffset).toISOString(),
        expiration_time: new Date(NOW + expiresOffset).toISOString(),
        content: { ...broadcast.content, subject },
    };
}

const oneOfEach = () => [
    broadcastBetween("Active", -1000, 1000),
    broadcastBetween("Scheduled", 1000, 2000),
    broadcastBetween("Expired", -2000, -1000),
];

async function mountBroadcastsList(broadcasts: BroadcastNotification[] = []) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });

    server.use(
        http.get("/api/notifications/broadcast", ({ response }) => {
            return response(200).json(broadcasts);
        }),
    );

    const wrapper = mount(BroadcastsList, {
        global: withPlugins(localVue, pinia),
        stubs: {
            FontAwesomeIcon: true,
        },
    });

    await flushPromises();

    return wrapper;
}

type Wrapper = Awaited<ReturnType<typeof mountBroadcastsList>>;

async function toggleFilters(wrapper: Wrapper, ...filters: Filter[]) {
    for (const filter of filters) {
        await wrapper.find(filterButtons[filter]).trigger("click");
    }
}

function shownSubjects(wrapper: Wrapper) {
    return wrapper
        .findAll(selectors.broadcastItem)
        .map((item) => item.findComponent(Heading).text())
        .sort();
}

describe("BroadcastsList.vue", () => {
    it("shows the empty-list alert when there are no broadcasts", async () => {
        const wrapper = await mountBroadcastsList();

        expect(wrapper.findAll(selectors.broadcastItem)).toHaveLength(0);
        expect(wrapper.find(selectors.emptyBroadcastsListAlert).exists()).toBe(true);
    });

    it("lists active, scheduled and expired broadcasts while every filter is on", async () => {
        const wrapper = await mountBroadcastsList(oneOfEach());

        expect(shownSubjects(wrapper)).toEqual(["Active", "Expired", "Scheduled"]);
        expect(wrapper.find(selectors.emptyBroadcastsListAlert).exists()).toBe(false);
    });

    it.each([
        { off: ["scheduled", "expired"], shown: "Active" },
        { off: ["active", "expired"], shown: "Scheduled" },
        { off: ["active", "scheduled"], shown: "Expired" },
    ] as const)("lists only the $shown broadcast with the $off filters off", async ({ off, shown }) => {
        const wrapper = await mountBroadcastsList(oneOfEach());

        await toggleFilters(wrapper, ...off);

        expect(shownSubjects(wrapper)).toEqual([shown]);
    });

    it("shows the empty-list alert with every filter off, and lists broadcasts again as filters are switched back on", async () => {
        const wrapper = await mountBroadcastsList(oneOfEach());

        await toggleFilters(wrapper, "active", "scheduled", "expired");
        expect(shownSubjects(wrapper)).toEqual([]);
        expect(wrapper.find(selectors.emptyBroadcastsListAlert).exists()).toBe(true);

        await toggleFilters(wrapper, "active");
        expect(shownSubjects(wrapper)).toEqual(["Active"]);

        await toggleFilters(wrapper, "scheduled");
        expect(shownSubjects(wrapper)).toEqual(["Active", "Scheduled"]);

        await toggleFilters(wrapper, "expired");
        expect(shownSubjects(wrapper)).toEqual(["Active", "Expired", "Scheduled"]);
    });
});
