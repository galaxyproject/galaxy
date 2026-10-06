import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useExportToAnotherGalaxyStore } from "@/stores/exportToAnotherGalaxyStore";

import ExportToAnotherGalaxy from "./ExportToAnotherGalaxy.vue";

const config = ref<{ enable_celery_tasks: boolean } | null>({ enable_celery_tasks: true });
vi.mock("@/composables/config", () => ({
    useConfig: () => ({ config, isConfigLoaded: ref(true) }),
}));

beforeEach(() => {
    config.value = { enable_celery_tasks: true };
});

function mountButton(extraProps = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    const wrapper = mount(ExportToAnotherGalaxy as object, {
        props: { historyId: "h1", contentId: "c1", contentName: "sample1", ...extraProps },
        global: withPlugins(getLocalVue(), pinia),
    });
    return { wrapper, store: useExportToAnotherGalaxyStore(pinia) };
}

describe("ExportToAnotherGalaxy", () => {
    it("opens the export dialog for its item", async () => {
        const { wrapper, store } = mountButton({ contentType: "dataset_collection", label: "Export" });
        const button = wrapper.find('[data-description="export to another galaxy"]');
        expect(button.text()).toBe("Export");
        await button.trigger("click");
        expect(store.open).toHaveBeenCalledWith({
            historyId: "h1",
            contentType: "dataset_collection",
            contentId: "c1",
            contentName: "sample1",
        });
    });

    it("renders nothing until the configuration has loaded", () => {
        config.value = null;
        const { wrapper } = mountButton();
        expect(wrapper.find('[data-description="export to another galaxy"]').exists()).toBe(false);
    });
});
