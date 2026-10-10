import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { useConfigStore } from "@/stores/configurationStore";

import * as FormToolStories from "./FormTool.stories";

import FormTool from "./FormTool.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";

const stories = composeStories(FormToolStories);
const mountStory = useStoryMount();

/** Mounts a story once the configuration the tool card reads has loaded. */
async function mountFormTool(story) {
    const wrapper = mountStory(story);
    await vi.waitFor(() => expect(useConfigStore().isLoaded).toBe(true));
    await flushPromises();
    return wrapper;
}

describe("FormTool", () => {
    it("emits the picked version's tool id and version when switching versions", async () => {
        const wrapper = await mountFormTool(stories.OlderToolVersion);

        const versionItems = wrapper.findAll(".tool-versions .dropdown-item");
        expect(versionItems.map((item) => item.text())).toEqual([
            "Switch to 0.74+galaxy1",
            "Switch to 0.73+galaxy0",
            "Selected 0.72+galaxy1",
        ]);
        const [switchToLatest, switchToMiddle] = versionItems;
        const emitted = () => wrapper.getComponent(FormTool).emitted("onSetData");

        await switchToMiddle.trigger("click");
        expect(emitted()[0][1]).toMatchObject({
            tool_version: "0.73+galaxy0",
            tool_id: "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.73+galaxy0",
        });

        await switchToLatest.trigger("click");
        expect(emitted()[1][1]).toMatchObject({
            tool_version: "0.74+galaxy1",
            tool_id: "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy1",
        });
    });

    describe("with a rules input", () => {
        async function mountedInputs() {
            const wrapper = await mountFormTool(stories.RulesParameter);
            const [text, rules] = wrapper.findComponent(FormDisplay).props("inputs");
            return { text, rules };
        }

        it("keeps UI-only metadata out of its nested mapping and rule entries", async () => {
            const { rules } = await mountedInputs();

            for (const entry of [rules.value.mapping[0], rules.value.rules[0]]) {
                expect(entry).not.toHaveProperty("collapsible_value");
                expect(entry).not.toHaveProperty("connectable");
                expect(entry).not.toHaveProperty("is_workflow");
            }
        });

        it("leaves the rules input runtime-editable and not connectable", async () => {
            const { rules } = await mountedInputs();

            expect(rules.collapsible_value).toBeUndefined();
            expect(rules.connectable).toBe(false);
        });

        it("still marks a sibling text input as a connectable runtime value", async () => {
            const { text } = await mountedInputs();

            expect(text.collapsible_value.__class__).toBe("RuntimeValue");
            expect(text.connectable).toBe(true);
        });
    });
});
