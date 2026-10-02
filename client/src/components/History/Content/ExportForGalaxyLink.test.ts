import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";

import ExportForGalaxyLink from "./ExportForGalaxyLink.vue";

const PREPARE = "/api/histories/{history_id}/contents/{type}s/{id}/prepare_store_download";

const config = ref({ enable_celery_tasks: true });
vi.mock("@/composables/config", () => ({
    useConfig: () => ({ config, isConfigLoaded: ref(true) }),
}));

const { server, http } = useServerMock();

let exportsStarted = 0;

// Long enough for a second export request, if one were sent, to reach the mock.
const flushRequests = () => new Promise((resolve) => setTimeout(resolve, 100));

beforeEach(() => {
    config.value = { enable_celery_tasks: true };
    exportsStarted = 0;
});

function mountButton(propsData = {}) {
    return mount(ExportForGalaxyLink as object, {
        localVue: getLocalVue(),
        propsData: { historyId: "h1", contentType: "dataset_collection", contentId: "c1", ...propsData },
    });
}

async function exportItem() {
    const wrapper = mountButton();
    await wrapper.find('[data-description="export for galaxy link"]').trigger("click");
    return wrapper;
}

function exportEndsIn(state: string, reason = "") {
    server.use(
        http.post(PREPARE, ({ response }) => {
            exportsStarted += 1;
            return response(200).json({ storage_request_id: "req1", task: { id: "task1" } } as never);
        }),
        http.get("/api/tasks/{task_id}/state", ({ response }) => response(200).json(state as never)),
        http.get("/api/tasks/{task_id}/result", ({ response }) =>
            response(200).json({ state, result: reason } as never),
        ),
    );
}

describe("ExportForGalaxyLink", () => {
    it("shows a label next to the icon when given one, as the collection buttons do", () => {
        const wrapper = mountButton({ label: "Galaxy Link" });
        expect(wrapper.find('[data-description="export for galaxy link"]').text()).toBe("Galaxy Link");
    });

    it("offers no button when this Galaxy runs no Celery tasks, since the export needs them", () => {
        config.value = { enable_celery_tasks: false };
        expect(mountButton().find('[data-description="export for galaxy link"]').exists()).toBe(false);
    });

    it("shows the link once the export has finished", async () => {
        exportEndsIn("SUCCESS");
        const wrapper = await exportItem();
        await vi.waitFor(() => expect(wrapper.find('[data-description="galaxy link"]').exists()).toBe(true));
        const link = wrapper.find('[data-description="galaxy link"]').element as HTMLInputElement;
        expect(link.value).toMatch(/^https?:\/\/.*\/api\/short_term_storage\/req1$/);
    });

    it("reopens the same link instead of exporting again", async () => {
        exportEndsIn("SUCCESS");
        const wrapper = await exportItem();
        await vi.waitFor(() => expect(wrapper.find('[data-description="galaxy link"]').exists()).toBe(true));
        await wrapper.find('[data-description="export for galaxy link"]').trigger("click");
        await flushRequests();
        expect(exportsStarted).toBe(1);
    });

    it("starts no second export while the first is still running", async () => {
        exportEndsIn("PENDING");
        const wrapper = await exportItem();
        await vi.waitFor(() => expect(exportsStarted).toBe(1));
        await wrapper.find('[data-description="export for galaxy link"]').trigger("click");
        await flushRequests();
        expect(exportsStarted).toBe(1);
    });

    it("shows why the export failed instead of a link", async () => {
        exportEndsIn("FAILURE", "Unknown error: the file is missing");
        const wrapper = await exportItem();
        await vi.waitFor(() => expect(wrapper.text()).toContain("Unknown error: the file is missing"));
        expect(wrapper.find('[data-description="galaxy link"]').exists()).toBe(false);
    });

    it("shows why the export could not start", async () => {
        server.use(
            http.post(PREPARE, ({ response }) =>
                response("4XX").json({ err_msg: "History is not accessible", err_code: 403 }, { status: 403 }),
            ),
        );
        const wrapper = await exportItem();
        await vi.waitFor(() => expect(wrapper.text()).toContain("History is not accessible"));
        expect(wrapper.find('[data-description="galaxy link"]').exists()).toBe(false);
    });
});
