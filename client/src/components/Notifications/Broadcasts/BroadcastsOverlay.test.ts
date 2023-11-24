import { setActivePinia } from "pinia";
import flushPromises from "flush-promises";
import { getLocalVue } from "@tests/jest/helpers";
import { createTestingPinia } from "@pinia/testing";
import BroadcastsOverlay from "./BroadcastsOverlay.vue";
import { shallowMount } from "@vue/test-utils";
import { type BroadcastNotification, useBroadcastsStore } from "@/stores/broadcastsStore";

const localVue = getLocalVue(true);

const now = new Date();
const inTwoMonths = new Date(new Date(now).setMonth(now.getMonth() + 2));

/** API date-time does not have timezone indicator and it's always UTC. */
function toApiDate(date: Date): string {
    return date.toISOString().replace("Z", "");
}

function generateBroadcastNotification(
    id: string,
    publicationTime?: Date,
    expirationTime?: Date
): BroadcastNotification {
    const publication_time = publicationTime ? toApiDate(publicationTime) : toApiDate(now);
    const expiration_time = expirationTime ? toApiDate(expirationTime) : toApiDate(inTwoMonths);
    return {
        id: id,
        create_time: toApiDate(now),
        update_time: toApiDate(now),
        publication_time,
        expiration_time,
        source: "testing",
        variant: "info",
        content: {
            subject: `Test subject ${id}`,
            message: `Test message ${id}`,
        },
    };
}

const FAKE_BROADCASTS: BroadcastNotification[] = [
    generateBroadcastNotification("1"),
    generateBroadcastNotification("2"),
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

    const wrapper = shallowMount(BroadcastsOverlay, {
        localVue,
        pinia,
    });

    await flushPromises();
    return wrapper;
}

describe("BroadcastsOverlay.vue", () => {
    it("should not render anything when there is no broadcast", async () => {
        const wrapper = await mountBroadcastsOverlayWith();

        expect(wrapper.exists()).toBe(true);
        expect(wrapper.html()).toBe("");
    });

    it("should render only one broadcast at a time", async () => {
        const wrapper = await mountBroadcastsOverlayWith(FAKE_BROADCASTS);
        expect(wrapper.findAll(".broadcast-message")).toHaveLength(1);
        expect(wrapper.find(".broadcast-message").text()).toContain("Test message 1");
    });

    it("should render the next broadcast when the current one is dismissed", async () => {
        const wrapper = await mountBroadcastsOverlayWith(FAKE_BROADCASTS);
        expect(wrapper.findAll(".broadcast-message")).toHaveLength(1);
        expect(wrapper.find(".broadcast-message").text()).toContain("Test message 1");

        const dismissButton = wrapper.find("#dismiss-button");
        await dismissButton.trigger("click");

        expect(wrapper.findAll(".broadcast-message")).toHaveLength(1);
        expect(wrapper.find(".broadcast-message").text()).toContain("Test message 2");
    });

    it("should not render the broadcast when it has expired", async () => {
        const expiredBroadcast = generateBroadcastNotification("expired", undefined, new Date(now));
        const wrapper = await mountBroadcastsOverlayWith([expiredBroadcast]);

        expect(wrapper.exists()).toBe(true);
        expect(wrapper.html()).toBe("");
    });

    it("should not render the broadcast when it has not been published yet", async () => {
        const unpublishedBroadcast = generateBroadcastNotification("unpublished", new Date(inTwoMonths));
        const wrapper = await mountBroadcastsOverlayWith([unpublishedBroadcast]);

        expect(wrapper.exists()).toBe(true);
        expect(wrapper.html()).toBe("");
    });
});
