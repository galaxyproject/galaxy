import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import {
    generateMessageNotification,
    generateNewSharedItemNotification,
    generateToolInstallationRequestNotification,
} from "@/components/Notifications/test-utils";
import { useNotificationsStore } from "@/stores/notificationsStore";

import NotificationCard from "@/components/Notifications/NotificationCard.vue";

const localVue = getLocalVue(true);

async function mountComponent(component: object, propsData: object = {}): Promise<Wrapper<Vue>> {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    const wrapper = mount(component, {
        localVue,
        propsData,
        pinia,
    });

    await flushPromises();
    return wrapper;
}

describe("Notifications categories", () => {
    it("render markdown in message notification", async () => {
        const notification = generateMessageNotification();
        notification.content.message = "This is a **markdown** message to test _rendering_";

        const wrapper = await mountComponent(NotificationCard, {
            notification,
        });

        expect(wrapper.find(`#g-card-description-${notification.id}`).html()).toContain(
            "This is a <strong>markdown</strong> message to test <em>rendering</em>",
        );
    });

    it("shared item notification show subject and message", async () => {
        const notification = generateNewSharedItemNotification();

        const wrapper = await mountComponent(NotificationCard, {
            notification,
        });

        expect(wrapper.text()).toContain(notification.content.item_type);
        expect(wrapper.text()).toContain(`The user ${notification.content.owner_name} shared`);

        expect(wrapper.find(`#g-card-description-${notification.id}`).text()).toContain(
            `The user ${notification.content.owner_name} shared`,
        );
        expect(wrapper.find(`#g-card-description-${notification.id}`).text()).toContain(
            `${notification.content.item_type}  with you`,
        );
    });

    it("mark as read", async () => {
        const notification = Math.random() > 0.5 ? generateMessageNotification() : generateNewSharedItemNotification();

        const wrapper = await mountComponent(NotificationCard, {
            notification: {
                ...notification,
                seen_time: null,
            },
        });

        const notificationsStore = useNotificationsStore();

        const spyOnUpdateNotification = vi.spyOn(notificationsStore, "updateNotification");
        spyOnUpdateNotification.mockImplementation(async (notification, changes) => {
            if (changes.deleted) {
                wrapper.setProps({
                    notification: null,
                });
            } else {
                wrapper.setProps({
                    notification: {
                        ...notification,
                        ...changes,
                    },
                });
            }
        });

        await flushPromises();

        spyOnUpdateNotification.mockImplementation(async (notification) => {
            wrapper.setProps({
                notification: {
                    ...notification,
                    seen_time: new Date().toISOString(),
                },
            });
        });

        const markAsReadButton = wrapper.find(`#g-card-action-mark-as-read-button-${notification.id}`);
        expect(markAsReadButton.exists()).toBe(true);
        await markAsReadButton.trigger("click");

        await nextTick();

        expect(spyOnUpdateNotification).toHaveBeenCalledTimes(1);

        expect(wrapper.find(`#g-card-action-expiration-time-button-${notification.id}`).exists()).toBe(true);
    });

    it("delete notification", async () => {
        const notification = Math.random() > 0.5 ? generateMessageNotification() : generateNewSharedItemNotification();

        const wrapper = await mountComponent(NotificationCard, {
            notification,
        });

        const notificationsStore = useNotificationsStore();

        const spyOnUpdateNotification = vi.spyOn(notificationsStore, "updateNotification");
        spyOnUpdateNotification.mockImplementation(async (_notification, changes) => {
            if (changes.deleted) {
                wrapper.setProps({
                    notification: null,
                });
            }
        });

        await flushPromises();

        const deleteButton = wrapper.find(`#g-card-action-delete-button-${notification.id}`);
        expect(deleteButton.exists()).toBe(true);
        await deleteButton.trigger("click");

        await nextTick();

        expect(spyOnUpdateNotification).toHaveBeenCalledTimes(1);
    });

    it("tool_installation_request notification shows tool name in title and details in description", async () => {
        const notification = generateToolInstallationRequestNotification();

        const wrapper = await mountComponent(NotificationCard, {
            notification,
        });

        // Title should include the first tool's label
        const firstTool = notification.content.tools[0]!;
        expect(wrapper.text()).toContain(firstTool.name);

        // Description area should show tool installation request details
        const descriptionArea = wrapper.find(`#g-card-description-${notification.id}`);
        expect(descriptionArea.text()).toContain(firstTool.description);
        expect(descriptionArea.text()).toContain(firstTool.scientific_domain);
        expect(descriptionArea.text()).toContain(firstTool.requested_version);
        expect(descriptionArea.text()).toContain(notification.content.requester_email);
    });

    it("tool_installation_request notification associates details with each tool in multi-tool requests", async () => {
        const notification = generateToolInstallationRequestNotification();
        notification.content.tools = [
            {
                name: "bwa",
                tool_shed_id: null,
                tool_url: null,
                description: "Aligner for short reads",
                scientific_domain: null,
                requested_version: null,
            },
            {
                name: "samtools",
                tool_shed_id: null,
                tool_url: null,
                description: "SAM/BAM utilities",
                scientific_domain: null,
                requested_version: "1.13",
            },
        ];

        const wrapper = await mountComponent(NotificationCard, {
            notification,
        });

        expect(wrapper.text()).toContain("Tool Installation Request: 2 tools");

        // Each tool's list item must contain its own details and not the other tool's.
        const toolItems = wrapper.findAll("ul:not(.list-unstyled) > li");
        expect(toolItems).toHaveLength(2);
        expect(toolItems.at(0).text()).toContain("bwa");
        expect(toolItems.at(0).text()).toContain("Aligner for short reads");
        expect(toolItems.at(0).text()).not.toContain("SAM/BAM utilities");
        expect(toolItems.at(1).text()).toContain("samtools");
        expect(toolItems.at(1).text()).toContain("SAM/BAM utilities");
        expect(toolItems.at(1).text()).toContain("1.13");
        expect(toolItems.at(1).text()).not.toContain("Aligner for short reads");
    });

    it("tool_installation_request notification links workflow id and exposes anchor for deep-linking", async () => {
        const notification = generateToolInstallationRequestNotification();
        notification.content.workflow_id = "encoded-workflow-id-abc";

        const wrapper = await mountComponent(NotificationCard, {
            notification,
        });

        expect(wrapper.html()).toContain(`/workflows/run?id=${notification.content.workflow_id}`);
        expect(wrapper.find(`#notification-card-${notification.id}`).exists()).toBe(true);
    });
});
