import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/schema";
import { sanitizeHtml } from "@/directives/sanitizeHtml";
import { getAppRoot } from "@/onload/loadConfig";
import { type BroadcastNotification, useBroadcastsStore } from "@/stores/broadcastsStore";

import BroadcastsOverlay from "./BroadcastsOverlay.vue";

vi.mock("@/onload/loadConfig", () => ({ getAppRoot: vi.fn(() => "/") }));

const localVue = getLocalVue(true);

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
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    const broadcastsStore = useBroadcastsStore();
    broadcastsStore.broadcasts = broadcasts;

    const spyOnDismissBroadcast = vi.spyOn(broadcastsStore, "dismissBroadcast");
    spyOnDismissBroadcast.mockImplementation(async (broadcast) => {
        broadcastsStore.broadcasts = broadcastsStore.broadcasts.filter((b) => b.id !== broadcast.id);
    });

    const wrapper = mount(BroadcastsOverlay as object, {
        global: localVue,
        pinia,
    });

    await flushPromises();
    return wrapper;
}

function broadcastWithActionLink(actionLink: components["schemas"]["ActionLink"]): BroadcastNotification {
    return generateBroadcastNotification({
        content: { category: "broadcast", subject: "Subject", message: "Message", action_links: [actionLink] },
    });
}

const messageCssSelector = ".broadcast-container .message";
const actionLinkSelector = ".action-links a";

describe("BroadcastsOverlay.vue", () => {
    beforeEach(() => {
        vi.mocked(getAppRoot).mockReturnValue("/");
    });

    it("opens a relative action link in a new tab under the app root", async () => {
        vi.mocked(getAppRoot).mockReturnValue("/galaxy/");
        const wrapper = await mountBroadcastsOverlayWith([
            broadcastWithActionLink({ action_name: "Costs", link: "/costs/", target: "_blank" }),
        ]);

        const link = wrapper.find(actionLinkSelector);
        expect(link.attributes("href")).toBe("/galaxy/costs/");
        expect(link.attributes("target")).toBe("_blank");
        expect(link.attributes("rel")).toBe("noopener noreferrer");
        expect(link.text()).toContain("opens in a new tab");
    });

    it("opens an external action link in a new tab", async () => {
        const wrapper = await mountBroadcastsOverlayWith([
            broadcastWithActionLink({ action_name: "External", link: "https://example.org", target: "_blank" }),
        ]);

        const link = wrapper.find(actionLinkSelector);
        expect(link.attributes("href")).toBe("https://example.org");
        expect(link.attributes("target")).toBe("_blank");
    });

    it("opens an action link in the current tab when the target is _self", async () => {
        const wrapper = await mountBroadcastsOverlayWith([
            broadcastWithActionLink({ action_name: "External", link: "https://example.org", target: "_self" }),
        ]);

        const link = wrapper.find(actionLinkSelector);
        expect(link.attributes("target")).toBeUndefined();
        expect(link.attributes("rel")).toBeUndefined();
        expect(link.text()).not.toContain("opens in a new tab");
    });

    it("should not render anything when there is no broadcast", async () => {
        const wrapper = await mountBroadcastsOverlayWith();

        expect(wrapper.exists()).toBe(true);
        expect(wrapper.find(".broadcast-container").exists()).toBe(false);
    });

    it("should render only one broadcast at a time", async () => {
        const wrapper = await mountBroadcastsOverlayWith(FAKE_BROADCASTS);
        expect(wrapper.findAll(messageCssSelector)).toHaveLength(1);
        expect(wrapper.find(messageCssSelector).text()).toContain("Test message 1");
    });

    it("should render the next broadcast when the current one is dismissed", async () => {
        const wrapper = await mountBroadcastsOverlayWith(FAKE_BROADCASTS);
        expect(wrapper.findAll(messageCssSelector)).toHaveLength(1);
        expect(wrapper.find(messageCssSelector).text()).toContain("Test message 1");

        const dismissButton = wrapper.find(".dismiss-button");
        await dismissButton.trigger("click");

        expect(wrapper.findAll(messageCssSelector)).toHaveLength(1);
        expect(wrapper.find(messageCssSelector).text()).toContain("Test message 2");
    });

    it("should show more important broadcasts first", async () => {
        const broadcasts = [
            generateBroadcastNotification({ id: "warning", variant: "warning" }),
            generateBroadcastNotification({ id: "info", variant: "info" }),
            generateBroadcastNotification({ id: "urgent", variant: "urgent" }),
        ];

        const wrapper = await mountBroadcastsOverlayWith(broadcasts);
        expect(wrapper.find(messageCssSelector).text()).toContain("Test message urgent");

        const dismissButton = wrapper.find(".dismiss-button");
        await dismissButton.trigger("click");
        expect(wrapper.find(messageCssSelector).text()).toContain("Test message warning");

        await dismissButton.trigger("click");
        expect(wrapper.find(messageCssSelector).text()).toContain("Test message info");
    });

    it("should allow cycling through broadcasts", async () => {
        const broadcasts = [
            generateBroadcastNotification({ id: "1" }),
            generateBroadcastNotification({ id: "2" }),
            generateBroadcastNotification({ id: "3" }),
        ];

        const wrapper = await mountBroadcastsOverlayWith(broadcasts);
        expect(wrapper.findAll(messageCssSelector)).toHaveLength(1);
        expect(wrapper.find(messageCssSelector).text()).toContain("Test message 1");

        const rightButton = wrapper.find("button.right");
        await rightButton.trigger("click");
        expect(wrapper.find(messageCssSelector).text()).toContain("Test message 2");

        await rightButton.trigger("click");
        expect(wrapper.find(messageCssSelector).text()).toContain("Test message 3");

        await rightButton.trigger("click");
        expect(wrapper.find(messageCssSelector).text()).toContain("Test message 1");

        const leftButton = wrapper.find("button.left");
        await leftButton.trigger("click");
        expect(wrapper.find(messageCssSelector).text()).toContain("Test message 3");

        await leftButton.trigger("click");
        expect(wrapper.find(messageCssSelector).text()).toContain("Test message 2");
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
        vi.mocked(sanitizeHtml).mockClear();
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
