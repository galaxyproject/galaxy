import { mount, type Wrapper } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import type { UpgradeMessage } from "./modules/utilities";

import StateUpgradeModal from "./StateUpgradeModal.vue";

const MODAL_CONTENT_SELECTOR = '[data-description="workflow state upgrade modal content"]';

describe("StateUpgradeModal.vue", () => {
    let wrapper: Wrapper<Vue>;

    async function mountWith(stateMessages: UpgradeMessage[]) {
        wrapper = mount(StateUpgradeModal as object, {
            propsData: {
                stateMessages,
            },
        });
        await nextTick();
    }

    it("should not render if there are no messages", async () => {
        const stateMessages: UpgradeMessage[] = [];
        await mountWith(stateMessages);
        expect(wrapper.find(MODAL_CONTENT_SELECTOR).exists()).toBeFalsy();
    });

    it("should render if there are messages", async () => {
        const stateMessages = [
            {
                stepIndex: 2,
                name: "step name",
                details: ["my message 1", "my message 2"],
            },
        ] as unknown as UpgradeMessage[];
        await mountWith(stateMessages);
        expect(wrapper.find(MODAL_CONTENT_SELECTOR).exists()).toBeTruthy();
    });

    async function mountSomeInitialMessagesAndDismiss() {
        const stateMessages = [
            {
                stepIndex: 2,
                name: "step name",
                details: ["my message 1", "my message 2"],
            },
        ] as unknown as UpgradeMessage[];
        await mountWith(stateMessages);

        // Close the modal by dispatching a "close" event on the dialog element
        wrapper.find("dialog").element.dispatchEvent(new Event("close"));

        await nextTick();

        expect(wrapper.find(MODAL_CONTENT_SELECTOR).exists()).toBeFalsy();
    }

    it("should re-render when passed new messages", async () => {
        await mountSomeInitialMessagesAndDismiss();
        const stateMessagesNew = [
            {
                stepIndex: 3,
                name: "step name",
                details: ["my message 1", "my message 2"],
            },
        ] as unknown as UpgradeMessage[];
        await wrapper.setProps({
            stateMessages: stateMessagesNew,
        });

        // Even though the modal was closed, it should re-open when new messages are passed in
        expect(wrapper.find(MODAL_CONTENT_SELECTOR).exists()).toBeTruthy();
    });

    it("should not re-render if sent empty messages", async () => {
        await mountSomeInitialMessagesAndDismiss();
        const stateMessagesNew: UpgradeMessage[] = [];
        await wrapper.setProps({
            stateMessages: stateMessagesNew,
        });

        expect(wrapper.find(MODAL_CONTENT_SELECTOR).exists()).toBeFalsy();
    });
});
