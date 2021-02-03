import { shallowMount, createLocalVue } from "@vue/test-utils";
import StateUpgradeModal from "./StateUpgradeModal";

const localVue = createLocalVue();

describe("StateUpgradeModal.vue", () => {
    let wrapper;

    async function mountWith(stateMessages) {
        wrapper = shallowMount(StateUpgradeModal, {
            propsData: {
                stateMessages,
            },
            localVue,
        });
        await wrapper.vm.$nextTick();
    }

    it("should not render if there are no messages", async () => {
        const stateMessages = [];
        await mountWith(stateMessages);
        expect(wrapper.vm.show).toBeFalsy();
    });

    it("should render if there are messages", async () => {
        const stateMessages = [
            {
                stepIndex: 2,
                stepName: "step name",
                details: ["my message 1", "my message 2"],
            },
        ];
        await mountWith(stateMessages);
        expect(wrapper.vm.show).toBeTruthy();
    });

    async function mountSomeInitialMessagesAndDismiss() {
        const stateMessages = [
            {
                stepIndex: 2,
                stepName: "step name",
                details: ["my message 1", "my message 2"],
            },
        ];
        await mountWith(stateMessages);
        wrapper.vm.show = false;
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.show).toBeFalsy();
    }

    it("should re-render when passed new messages", async () => {
        await mountSomeInitialMessagesAndDismiss();
        const stateMessagesNew = [
            {
                stepIndex: 3,
                stepName: "step name",
                details: ["my message 1", "my message 2"],
            },
        ];
        await wrapper.setProps({
            stateMessages: stateMessagesNew,
        });
        expect(wrapper.vm.show).toBeTruthy();
    });

    it("should not re-render if sent empty messages", async () => {
        await mountSomeInitialMessagesAndDismiss();
        const stateMessagesNew = [];
        await wrapper.setProps({
            stateMessages: stateMessagesNew,
        });
        expect(wrapper.vm.show).toBeFalsy();
    });
});
