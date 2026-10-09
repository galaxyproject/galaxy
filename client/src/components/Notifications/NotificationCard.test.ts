import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, RouterLinkStub, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { UserNotification } from "@/api/notifications";
import {
    generateMessageNotification,
    generateNewSharedItemNotification,
    generateToolInstallationRequestNotification,
} from "@/components/Notifications/test-utils";
import { sanitizeHtml } from "@/directives/sanitizeHtml";
import { useNotificationsStore } from "@/stores/notificationsStore";

import NotificationCard from "@/components/Notifications/NotificationCard.vue";

const localVue = getLocalVue(true);

enableAutoUnmount(afterEach);

async function mountNotificationCard(notification: UserNotification): Promise<VueWrapper> {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    // Render GCard's slots and action buttons so interactions exercise the card's real UI.
    const wrapper = mount(NotificationCard, {
        props: { notification },
        global: {
            ...withPlugins(localVue, pinia),
            stubs: { ...localVue.stubs, RouterLink: RouterLinkStub },
        },
    });

    await flushPromises();
    return wrapper;
}

describe("NotificationCard", () => {
    it("renders markdown in message notifications", async () => {
        const notification = generateMessageNotification();
        notification.content.message = "This is a **markdown** message to test _rendering_";

        const wrapper = await mountNotificationCard(notification);

        expect(wrapper.find(`#g-card-description-${notification.id}`).html()).toContain(
            "This is a <strong>markdown</strong> message to test <em>rendering</em>",
        );
    });

    it("shows the shared item type and owner", async () => {
        const notification = generateNewSharedItemNotification();

        const wrapper = await mountNotificationCard(notification);

        expect(wrapper.text()).toContain(notification.content.item_type);
        expect(wrapper.text()).toContain(`The user ${notification.content.owner_name} shared`);

        const description = wrapper.find(`#g-card-description-${notification.id}`).text();
        expect(description).toContain(`The user ${notification.content.owner_name} shared`);
        expect(description).toContain(`${notification.content.item_type}  with you`);
    });

    describe.each([
        { category: "message", createNotification: generateMessageNotification },
        { category: "new_shared_item", createNotification: generateNewSharedItemNotification },
    ])("$category notification actions", ({ createNotification }) => {
        it("marks an unread notification as read and shows its expiration action", async () => {
            const notification = { ...createNotification(), seen_time: null };
            const wrapper = await mountNotificationCard(notification);
            const notificationsStore = useNotificationsStore();
            const updateNotification = vi.spyOn(notificationsStore, "updateNotification");
            updateNotification.mockImplementation(async (updatedNotification) => {
                await wrapper.setProps({
                    notification: {
                        ...updatedNotification,
                        seen_time: "2024-01-01T12:00:00.000Z",
                    },
                });
            });

            const markAsReadButton = wrapper.find(`#g-card-action-mark-as-read-button-${notification.id}`);
            expect(markAsReadButton.exists()).toBe(true);
            await markAsReadButton.trigger("click");
            await flushPromises();

            expect(updateNotification).toHaveBeenCalledTimes(1);
            expect(updateNotification).toHaveBeenCalledWith(notification, { seen: true });
            expect(wrapper.find(`#g-card-action-mark-as-read-button-${notification.id}`).exists()).toBe(false);
            expect(wrapper.find(`#g-card-action-expiration-time-button-${notification.id}`).exists()).toBe(true);
        });

        it("deletes a notification when its delete action is clicked", async () => {
            const notification = { ...createNotification(), seen_time: "2024-01-01T12:00:00.000Z" };
            const wrapper = await mountNotificationCard(notification);
            const notificationsStore = useNotificationsStore();
            const updateNotification = vi.spyOn(notificationsStore, "updateNotification");
            updateNotification.mockImplementation(async (_notification, changes) => {
                if (changes.deleted) {
                    await wrapper.setProps({ notification: null });
                }
            });

            const deleteButton = wrapper.find(`#g-card-action-delete-button-${notification.id}`);
            expect(deleteButton.exists()).toBe(true);
            await deleteButton.trigger("click");
            await flushPromises();

            expect(updateNotification).toHaveBeenCalledTimes(1);
            expect(updateNotification).toHaveBeenCalledWith(notification, { deleted: true });
            expect(wrapper.find(`#notification-card-${notification.id}`).exists()).toBe(false);
        });
    });

    it("renders the message markdown through v-sanitize-html", async () => {
        vi.mocked(sanitizeHtml).mockClear();
        const notification = generateMessageNotification();
        notification.content.message = "A [link](/histories/list) and <b>raw</b>";

        await mountNotificationCard(notification);

        const call = vi.mocked(sanitizeHtml).mock.calls.find(([html]) => html?.includes("/histories/list"));
        expect(call?.[1]).toBe("default");
        expect(call?.[0]).toContain('<a href="/histories/list">link</a>');
        expect(call?.[0]).toContain("&lt;b&gt;raw&lt;/b&gt;");
    });

    it("shows the requested tool in the title and its details in the description", async () => {
        const notification = generateToolInstallationRequestNotification();

        const wrapper = await mountNotificationCard(notification);

        const firstTool = nth(notification.content.tools, 0);
        expect(wrapper.find(`#g-card-title-${notification.id}`).text()).toContain(firstTool.name);

        const descriptionArea = wrapper.find(`#g-card-description-${notification.id}`);
        expect(descriptionArea.text()).toContain(firstTool.description);
        expect(descriptionArea.text()).toContain(firstTool.scientific_domain);
        expect(descriptionArea.text()).toContain(firstTool.requested_version);
        expect(descriptionArea.text()).toContain(notification.content.requester_email);
    });

    it("shows the tool shed ID alongside the requested tool name", async () => {
        const notification = generateToolInstallationRequestNotification();
        notification.content.tools = [
            {
                name: "bwa",
                tool_shed_id: "toolshed.g2.bx.psu.edu/repos/devteam/bwa",
                tool_url: null,
                description: null,
                scientific_domain: null,
                requested_version: "0.7.17",
            },
        ];

        const wrapper = await mountNotificationCard(notification);

        const descriptionArea = wrapper.find(`#g-card-description-${notification.id}`);
        expect(descriptionArea.text()).toContain("Tool shed ID");
        expect(descriptionArea.text()).toContain("toolshed.g2.bx.psu.edu/repos/devteam/bwa");
    });

    it("associates each tool with its own details in requests for multiple tools", async () => {
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

        const wrapper = await mountNotificationCard(notification);

        expect(wrapper.find(`#g-card-title-${notification.id}`).text()).toContain("Tool Installation Request: 2 tools");

        // Each tool's list item must contain its own details and not the other tool's.
        const toolItems = wrapper.findAll("ul:not(.list-unstyled) > li");
        expect(toolItems).toHaveLength(2);
        const bwaDetails = nth(toolItems, 0).text();
        expect(bwaDetails).toContain("bwa");
        expect(bwaDetails).toContain("Aligner for short reads");
        expect(bwaDetails).not.toContain("SAM/BAM utilities");

        const samtoolsDetails = nth(toolItems, 1).text();
        expect(samtoolsDetails).toContain("samtools");
        expect(samtoolsDetails).toContain("SAM/BAM utilities");
        expect(samtoolsDetails).toContain("1.13");
        expect(samtoolsDetails).not.toContain("Aligner for short reads");
    });

    it("links the requested workflow to its run page", async () => {
        const notification = generateToolInstallationRequestNotification();
        notification.content.workflow_id = "encoded-workflow-id-abc";

        const wrapper = await mountNotificationCard(notification);

        const workflowLink = wrapper.findComponent(RouterLinkStub);
        expect(workflowLink.exists()).toBe(true);
        expect(workflowLink.props("to")).toBe(`/workflows/run?id=${notification.content.workflow_id}`);
    });
});
