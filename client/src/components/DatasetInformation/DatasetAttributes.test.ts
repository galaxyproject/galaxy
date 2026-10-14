import { composeStory } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import * as DatasetAttributesStories from "./DatasetAttributes.stories";

import DatasetAttributes from "./DatasetAttributes.vue";

const { server, http } = useServerMock();
const mountStory = useStoryMount();

async function mountDatasetAttributes() {
    // Keep the original synthetic save message only in this unit contract.
    const story = composeStory(
        {
            ...DatasetAttributesStories.EditableBed,
            parameters: {
                msw: {
                    handlers: {
                        save: http.untyped.put("/dataset/set_edit", () =>
                            HttpResponse.json({ message: "success", status: "success" }),
                        ),
                    },
                },
            },
        },
        DatasetAttributesStories.default,
    );
    const root = mountStory(story);
    await vi.waitFor(() => root.getComponent(DatasetAttributes));
    await flushPromises();
    return root.getComponent(DatasetAttributes);
}

describe("DatasetAttributes", () => {
    it("shows a successful save", async () => {
        const wrapper = await mountDatasetAttributes();

        const saveButton = wrapper.get("#dataset-attributes-default-save");

        await saveButton.trigger("click");

        await flushPromises();

        expect(wrapper.get(".dataset-attributes-alert").text()).toBe("success");
    });

    it("shows why saving failed", async () => {
        const wrapper = await mountDatasetAttributes();
        server.use(
            http.untyped.put("/dataset/set_edit", () => {
                return HttpResponse.json({ err_msg: "This dataset is encrypted." }, { status: 400 });
            }),
        );

        await wrapper.get("#dataset-attributes-default-save").trigger("click");
        await flushPromises();

        expect(wrapper.get(".dataset-attributes-alert").text()).toBe("This dataset is encrypted.");
    });
});
