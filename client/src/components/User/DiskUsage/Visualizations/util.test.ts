import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { expect, it, vi } from "vitest";
import { defineComponent } from "vue";

import { useDataLoading } from "./util";

const { errorToast } = vi.hoisted(() => ({ errorToast: vi.fn() }));

vi.mock("@/composables/toast", () => ({
    useToast: () => ({ error: errorToast, success: vi.fn() }),
}));

it("reports a failed load and stops loading", async () => {
    const { isLoading, loadDataOnMount } = useDataLoading();
    mount(
        defineComponent({
            setup() {
                loadDataOnMount(async () => {
                    throw new TypeError("Failed to fetch");
                });
                return {};
            },
            template: "<div />",
        }),
    );
    await flushPromises();
    expect(isLoading.value).toBe(false);
    expect(errorToast).toHaveBeenCalledWith("Failed to fetch", "An error occurred while loading storage data.");
});
