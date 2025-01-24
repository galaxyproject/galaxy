import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";

import { type BroadcastNotification, useBroadcastsStore } from "@/stores/broadcastsStore";

import BroadcastsOverlay from "./BroadcastsOverlay.vue";

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
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    const broadcastsStore = useBroadcastsStore();
    broadcastsStore.broadcasts = broadcasts;

    const spyOnDismissBroadcast = jest.spyOn(broadcastsStore, "dismissBroadcast");
    spyOnDismissBroadcast.mockImplementation(async (broadcast) => {
        broadcastsStore.broadcasts = broadcastsStore.broadcasts.filter((b) => b.id !== broadcast.id);
    });

    const wrapper = mount(BroadcastsOverlay, {
        localVue,
        pinia,
        stubs: {
            BroadcastContainer: true,
        },
    });

    await flushPromises();
    return wrapper;
}

const messageCssSelector = ".broadcast-container .message";

describe("BroadcastsOverlay.vue", () => {
    it("should not render anything when there is no broadcast", async () => {
        const wrapper = await mountBroadcastsOverlayWith();

        expect(wrapper.exists()).toBe(true);
        expect(wrapper.html()).toBe("");
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
        expect(wrapper.html()).toBe("");
    });

    it("should not render the broadcast when it has not been published yet", async () => {
        const unpublishedBroadcast = generateBroadcastNotification({
            id: "unpublished",
            publication_time: toApiDate(inTwoMonths),
        });
        const wrapper = await mountBroadcastsOverlayWith([unpublishedBroadcast]);

        expect(wrapper.exists()).toBe(true);
        expect(wrapper.html()).toBe("");
    });
});
