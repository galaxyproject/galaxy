import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { Toast, useToast } from "@/composables/toast";

import * as componentStories from "./InstanceDropdown.stories";

import ObjectStoreInstanceDropdown from "./InstanceDropdown.vue";
import ConfigurationInstanceDropdown from "@/components/ConfigTemplates/InstanceDropdown.vue";

vi.mock("@/composables/toast", { spy: true });

const toastError = vi.mocked(Toast.error);
const { server, http } = useServerMock();
const stories = composeStories(componentStories);
const mountStory = useStoryMount();

describe("Object Store Instance Dropdown", () => {
    beforeEach(() => toastError.mockClear());
    afterEach(() => useToast().clearToasts());

    it("emits entryRemoved when remove succeeds", async () => {
        const requestBodies: unknown[] = [];
        const wrapper = mountStory(stories.RemovableStorage).getComponent(ObjectStoreInstanceDropdown);
        server.use(
            http.put("/api/object_store_instances/{uuid}", async ({ request }) => {
                requestBodies.push(await request.clone().json());
                // Observe the request, then let the story echo the update in its real response model.
            }),
        );

        wrapper.getComponent(ConfigurationInstanceDropdown).vm.$emit("remove");
        await flushPromises();

        expect(requestBodies).toEqual([{ hidden: true }]);
        await vi.waitFor(() => expect(wrapper.emitted("entryRemoved")).toBeTruthy());
        expect(toastError).not.toHaveBeenCalled();
    });

    it("shows toast and does not emit entryRemoved when remove fails", async () => {
        const wrapper = mountStory(stories.StorageNoLongerExists).getComponent(ObjectStoreInstanceDropdown);
        // Preserve the original synthetic error and exact toast assertion; the standalone story uses Galaxy's real error.
        server.use(
            http.put("/api/object_store_instances/{uuid}", ({ response }) =>
                response("4XX").json({ err_code: 400, err_msg: "Unable to remove" }, { status: 400 }),
            ),
        );

        wrapper.getComponent(ConfigurationInstanceDropdown).vm.$emit("remove");
        await flushPromises();

        expect(toastError).toHaveBeenCalledWith("Unable to remove", "Failed to remove instance");
        expect(wrapper.emitted("entryRemoved")).toBeFalsy();
    });
});
