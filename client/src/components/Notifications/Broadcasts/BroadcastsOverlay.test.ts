import { composeStory } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { disposePinia, getActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";
import { type BroadcastNotification, useBroadcastsStore } from "@/stores/broadcastsStore";

import * as Stories from "./BroadcastsOverlay.stories";
import { broadcastsState } from "./test_fixtures";

import BroadcastsOverlay from "./BroadcastsOverlay.vue";

// Exercise the decorator's real per-user persistent state rather than global unit mocks.
vi.unmock("@/composables/hashedUserId");
vi.unmock("@/composables/userLocalStorage");

const mountStory = useStoryMount();

const now = new Date();
const inTwoMonths = new Date(new Date(now).setMonth(now.getMonth() + 2));

/** API date-time does not have timezone indicator and it's always UTC. */
function toApiDate(date: Date): string {
    return date.toISOString().replace("Z", "");
}

let idCounter = 0;

function generateBroadcastNotification(overwrites: Partial<BroadcastNotification> = {}): BroadcastNotification {
    const id = `${idCounter++}`;

    return {
        id: id,
        create_time: toApiDate(now),
        update_time: toApiDate(now),
        publication_time: toApiDate(now),
        expiration_time: toApiDate(inTwoMonths),
        source: "testing",
        variant: "info",
        category: "broadcast",
        content: {
            category: "broadcast",
            subject: `Test subject ${overwrites.id ?? id}`,
            message: `Test message ${overwrites.id ?? id}`,
        },
        ...overwrites,
    };
}

const FAKE_BROADCASTS: BroadcastNotification[] = [
    generateBroadcastNotification({ id: "1" }),
    generateBroadcastNotification({ id: "2" }),
];

async function mountBroadcastsOverlayWith(broadcasts: BroadcastNotification[] = []) {
    const story = composeStory(
        { ...Stories.NoticesQueue, parameters: broadcastsState(() => broadcasts) },
        Stories.default,
    );
    const root = mountStory(story, { instrumentLocalization: true, pinia: { stubActions: true } });
    const pinia = getActivePinia()!;
    onTestFinished(() => disposePinia(pinia));
    await vi.waitFor(() => {
        if (!root.findComponent(BroadcastsOverlay).exists()) {
            throw new Error("Broadcast fixture is still initializing.");
        }
    });
    const broadcastsStore = useBroadcastsStore(pinia);
    const spyOnDismissBroadcast = vi.spyOn(broadcastsStore, "dismissBroadcast");
    spyOnDismissBroadcast.mockImplementation(async (broadcast) => {
        broadcastsStore.broadcasts = broadcastsStore.broadcasts.filter((b) => b.id !== broadcast.id);
    });
    const wrapper = root.findComponent(BroadcastsOverlay);
    await flushPromises();
    return wrapper;
}

const messageCssSelector = ".broadcast-container .message";

describe("BroadcastsOverlay.vue", () => {
    beforeEach(() => {
        vi.mocked(sanitizeHtml).mockClear();
    });
    afterEach(() => {
        vi.restoreAllMocks();
        vi.mocked(sanitizeHtml).mockClear();
    });

    it("should not render anything when there is no broadcast", async () => {
        const wrapper = await mountBroadcastsOverlayWith();

        expect(wrapper.exists()).toBe(true);
        expect(wrapper.find(".broadcast-container").exists()).toBe(false);
    });

    it("should render only one broadcast at a time", async () => {
        const wrapper = await mountBroadcastsOverlayWith(FAKE_BROADCASTS);
        expect(wrapper.findAll(messageCssSelector)).toHaveLength(1);
        expect(wrapper.get(messageCssSelector).text()).toContain("Test message 1");
    });

    it("should render the next broadcast when the current one is dismissed", async () => {
        const wrapper = await mountBroadcastsOverlayWith(FAKE_BROADCASTS);
        expect(wrapper.findAll(messageCssSelector)).toHaveLength(1);
        expect(wrapper.get(messageCssSelector).text()).toContain("Test message 1");

        const dismissButton = wrapper.get(".dismiss-button");
        await dismissButton.trigger("click");

        expect(wrapper.findAll(messageCssSelector)).toHaveLength(1);
        expect(wrapper.get(messageCssSelector).text()).toContain("Test message 2");
    });

    it("should show more important broadcasts first", async () => {
        const broadcasts = [
            generateBroadcastNotification({ id: "warning", variant: "warning" }),
            generateBroadcastNotification({ id: "info", variant: "info" }),
            generateBroadcastNotification({ id: "urgent", variant: "urgent" }),
        ];

        const wrapper = await mountBroadcastsOverlayWith(broadcasts);
        expect(wrapper.get(messageCssSelector).text()).toContain("Test message urgent");

        const dismissButton = wrapper.get(".dismiss-button");
        await dismissButton.trigger("click");
        expect(wrapper.get(messageCssSelector).text()).toContain("Test message warning");

        await dismissButton.trigger("click");
        expect(wrapper.get(messageCssSelector).text()).toContain("Test message info");
    });

    it("should allow cycling through broadcasts", async () => {
        const broadcasts = [
            generateBroadcastNotification({ id: "1" }),
            generateBroadcastNotification({ id: "2" }),
            generateBroadcastNotification({ id: "3" }),
        ];

        const wrapper = await mountBroadcastsOverlayWith(broadcasts);
        expect(wrapper.findAll(messageCssSelector)).toHaveLength(1);
        expect(wrapper.get(messageCssSelector).text()).toContain("Test message 1");

        const rightButton = wrapper.get("button.right");
        await rightButton.trigger("click");
        expect(wrapper.get(messageCssSelector).text()).toContain("Test message 2");

        await rightButton.trigger("click");
        expect(wrapper.get(messageCssSelector).text()).toContain("Test message 3");

        await rightButton.trigger("click");
        expect(wrapper.get(messageCssSelector).text()).toContain("Test message 1");

        const leftButton = wrapper.get("button.left");
        await leftButton.trigger("click");
        expect(wrapper.get(messageCssSelector).text()).toContain("Test message 3");

        await leftButton.trigger("click");
        expect(wrapper.get(messageCssSelector).text()).toContain("Test message 2");
    });

    it("should not render the broadcast when it has expired", async () => {
        const expiredBroadcast = generateBroadcastNotification({ id: "expired", expiration_time: toApiDate(now) });
        const wrapper = await mountBroadcastsOverlayWith([expiredBroadcast]);

        expect(wrapper.exists()).toBe(true);
        expect(wrapper.find(".broadcast-container").exists()).toBe(false);
    });

    it("should not render the broadcast when it has not been published yet", async () => {
        const unpublishedBroadcast = generateBroadcastNotification({
            id: "unpublished",
            publication_time: toApiDate(inTwoMonths),
        });
        const wrapper = await mountBroadcastsOverlayWith([unpublishedBroadcast]);

        expect(wrapper.exists()).toBe(true);
        expect(wrapper.find(".broadcast-container").exists()).toBe(false);
    });

    it("renders the broadcast message through v-sanitize-html with the links profile", async () => {
        await mountBroadcastsOverlayWith([
            generateBroadcastNotification({
                id: "links",
                content: { category: "broadcast", subject: "s", message: "See [docs](https://example.org)" },
            }),
        ]);
        const call = vi.mocked(sanitizeHtml).mock.calls.find(([html]) => html?.includes(">docs</a>"));
        expect(call?.[1]).toBe("links");
        expect(call?.[0]).toContain('target="_blank"');
    });
});
