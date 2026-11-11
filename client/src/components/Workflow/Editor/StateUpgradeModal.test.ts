import { mount, type VueWrapper } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import type { UpgradeMessage } from "./modules/utilities";

import StateUpgradeModal from "./StateUpgradeModal.vue";

const MODAL_CONTENT_SELECTOR = '[data-description="workflow state upgrade modal content"]';

function upgradeMessage(overrides: Partial<UpgradeMessage> = {}): UpgradeMessage {
    return {
        stepIndex: "2",
        name: "step name",
        details: ["my message 1", "my message 2"],
        iconType: "",
        label: "",
        ...overrides,
    };
}

describe("StateUpgradeModal.vue", () => {
    let wrapper: VueWrapper;

    async function mountWith(stateMessages: UpgradeMessage[], filledDefaults: UpgradeMessage[] = []) {
        wrapper = mount(StateUpgradeModal as object, {
            propsData: {
                stateMessages,
                filledDefaults,
            },
        });
        await nextTick();
    }

    const FILLED = '[data-description="workflow state upgrade filled defaults"]';
    const REVIEW = '[data-description="workflow state upgrade review"]';
    const filledDefaults = [
        upgradeMessage({
            stepIndex: "1",
            name: "FastQC",
            details: ["No value found for 'Adapter list'.", "No value found for 'Kmers'."],
        }),
        upgradeMessage({ stepIndex: "4", name: "MultiQC", details: ["No value found for 'Report title'."] }),
    ];
    const toReview = [upgradeMessage({ name: "step", details: ["Tool version changed"] })];

    it("should not render if there are no messages", async () => {
        const stateMessages: UpgradeMessage[] = [];
        await mountWith(stateMessages);
        expect(wrapper.find(MODAL_CONTENT_SELECTOR).exists()).toBeFalsy();
    });

    it("should render if there are messages", async () => {
        const stateMessages = [upgradeMessage()];
        await mountWith(stateMessages);
        expect(wrapper.find(MODAL_CONTENT_SELECTOR).exists()).toBeTruthy();
    });

    async function mountSomeInitialMessagesAndDismiss() {
        const stateMessages = [upgradeMessage()];
        await mountWith(stateMessages);

        // Close the modal by dispatching a "close" event on the dialog element
        wrapper.find("dialog").element.dispatchEvent(new Event("close"));

        await nextTick();

        expect(wrapper.find(MODAL_CONTENT_SELECTOR).exists()).toBeFalsy();
    }

    it("should re-render when passed new messages", async () => {
        await mountSomeInitialMessagesAndDismiss();
        const stateMessagesNew = [upgradeMessage({ stepIndex: "3" })];
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

    it("renders upgrade details through v-sanitize-html with the links profile", async () => {
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
        const detail =
            'Tool version changed, see <a href="https://toolshed.g2.bx.psu.edu" target="_blank">the Tool Shed</a>';
        await mountWith([upgradeMessage({ stepIndex: "1", name: "step", details: [detail] })]);

        expect(sanitizeHtml).toHaveBeenCalledWith(detail, "links");
        expect(wrapper.find(".workflow-state-upgrade-step-details .sanitized a").exists()).toBe(true);
    });

    it("summarizes filled defaults, collapsed, when there is nothing to review", async () => {
        await mountWith([], filledDefaults);
        const filled = wrapper.find(FILLED);
        expect(wrapper.find(REVIEW).exists()).toBe(false);
        expect(filled.text()).toContain("Galaxy filled in 3 default values in 2 steps");
        expect(wrapper.text()).toContain("Default values filled in");
        const toggle = filled.find('[data-description="workflow state upgrade filled defaults toggle"]');
        expect(toggle.attributes("aria-pressed")).toBe("false");
        expect(toggle.text()).toContain("Show values");

        await toggle.trigger("click");
        expect(toggle.attributes("aria-pressed")).toBe("true");
        expect(toggle.text()).toContain("Hide values");
    });

    it("keeps problems to review separate from filled defaults", async () => {
        await mountWith(toReview, filledDefaults);
        expect(wrapper.text()).toContain("Issues loading this workflow");
        expect(wrapper.find(REVIEW).text()).toContain("Tool version changed");
        expect(wrapper.find(REVIEW).text()).not.toContain("Adapter list");
        expect(wrapper.find(FILLED).exists()).toBe(true);
    });

    it.each([
        ["Accept", [], filledDefaults, 1],
        ["Accept defaults", toReview, filledDefaults, 1],
        ["OK", toReview, [], undefined],
    ])("closes on %s and reports acceptance only for filled defaults", async (label, review, filled, accepted) => {
        await mountWith(review, filled);
        const ok = wrapper.find('[data-description="workflow state upgrade modal ok"]');
        expect(ok.text()).toBe(label);
        await ok.trigger("click");
        expect(wrapper.find(MODAL_CONTENT_SELECTOR).exists()).toBe(false);
        expect(wrapper.emitted("accept")?.length).toBe(accepted);
    });
});
