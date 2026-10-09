import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import type { UpgradeMessage } from "./modules/utilities";

import StateUpgradeModal from "./StateUpgradeModal.vue";

const MODAL_CONTENT_SELECTOR = '[data-description="workflow state upgrade modal content"]';

enableAutoUnmount(afterEach);
afterEach(() => {
    vi.mocked(sanitizeHtml).mockReset();
    vi.mocked(sanitizeHtml).mockImplementation((html) => html ?? "");
});

function makeMessage(overrides: Partial<UpgradeMessage> = {}): UpgradeMessage {
    return {
        stepIndex: "2",
        name: "step name",
        details: ["my message 1", "my message 2"],
        iconType: "",
        label: "",
        ...overrides,
    };
}

async function mountWith(stateMessages: UpgradeMessage[]) {
    const wrapper = mount(StateUpgradeModal, { props: { stateMessages } });
    await nextTick();
    return wrapper;
}

describe("StateUpgradeModal", () => {
    it("hides the content when there are no upgrade messages", async () => {
        const wrapper = await mountWith([]);
        expect(wrapper.find(MODAL_CONTENT_SELECTOR).exists()).toBe(false);
    });

    it("renders upgrade messages", async () => {
        const wrapper = await mountWith([makeMessage()]);
        expect(wrapper.find(MODAL_CONTENT_SELECTOR).exists()).toBe(true);
        expect(wrapper.find(".workflow-state-upgrade-step-summaries b").text()).toBe("Step 3: step name");
        expect(wrapper.findAll(".workflow-state-upgrade-step-details li").map((item) => item.text())).toEqual([
            "my message 1",
            "my message 2",
        ]);
    });

    it.each([
        { name: "reopens for new messages", messages: [makeMessage({ stepIndex: "3" })], visible: true },
        { name: "stays closed for empty messages", messages: [], visible: false },
    ])("$name after dismissal", async ({ messages, visible }) => {
        const wrapper = await mountWith([makeMessage()]);
        wrapper.find("dialog").element.dispatchEvent(new Event("close"));
        await nextTick();
        expect(wrapper.find(MODAL_CONTENT_SELECTOR).exists()).toBe(false);

        await wrapper.setProps({ stateMessages: messages });

        expect(wrapper.find(MODAL_CONTENT_SELECTOR).exists()).toBe(visible);
    });

    it("renders upgrade details through v-sanitize-html with the links profile", async () => {
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
        const detail =
            'Tool version changed, see <a href="https://toolshed.g2.bx.psu.edu" target="_blank">the Tool Shed</a>';
        const wrapper = await mountWith([makeMessage({ stepIndex: "1", name: "step", details: [detail] })]);

        expect(sanitizeHtml).toHaveBeenCalledWith(detail, "links");
        expect(wrapper.find(".workflow-state-upgrade-step-details .sanitized a").exists()).toBe(true);
    });
});
