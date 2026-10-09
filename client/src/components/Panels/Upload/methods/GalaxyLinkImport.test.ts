import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import GalaxyLinkImport from "./GalaxyLinkImport.vue";

const IMPORT = "/api/histories/{history_id}/contents_from_store_async";

const { server, http } = useServerMock();

function importEndsIn(state: string, reason = "") {
    const bodies: Record<string, unknown>[] = [];
    server.use(
        http.post(IMPORT, async ({ request, response }) => {
            bodies.push(await request.json());
            return response(200).json({ id: "task1", ignored: false } as never);
        }),
        http.get("/api/tasks/{task_id}/state", ({ response }) => response(200).json(state as never)),
        http.get("/api/tasks/{task_id}/result", ({ response }) =>
            response(200).json({ state, result: reason } as never),
        ),
    );
    return bodies;
}

async function importLink(link: string) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    const localVue = getLocalVue();
    const wrapper = mount(GalaxyLinkImport as object, {
        props: { method: { id: "galaxy-link" }, targetHistoryId: "hist_1" },
        global: { ...withPlugins(localVue, pinia), stubs: { ...localVue.stubs, SwitchToHistoryLink: true } },
    });
    await wrapper.find('[data-description="galaxy link input"]').setValue(link);
    await wrapper.find('[data-description="galaxy link import"]').trigger("click");
    return wrapper;
}

describe("GalaxyLinkImport", () => {
    it("imports the trimmed link in the background and says when it is done", async () => {
        const bodies = importEndsIn("SUCCESS");
        const wrapper = await importLink("  https://usegalaxy.org/api/short_term_storage/abc\n");
        await vi.waitFor(() => expect(wrapper.text()).toContain("Done!"));
        const input = wrapper.find('[data-description="galaxy link input"]').element as HTMLInputElement;
        expect(input.value).toBe("");
        expect(wrapper.find('[data-description="galaxy link import"]').attributes("aria-disabled")).toBe("true");
        expect(bodies[0]).toEqual({
            store_content_uri: "https://usegalaxy.org/api/short_term_storage/abc",
            model_store_format: "tar.gz",
            discarded_data: "forbid",
        });
    });

    it("stops and explains when the import fails", async () => {
        importEndsIn("FAILURE", "404 Not Found");
        const wrapper = await importLink("https://usegalaxy.org/api/short_term_storage/old");
        await vi.waitFor(() => expect(wrapper.text()).toContain("may have expired"));
        expect(wrapper.text()).toContain("404 Not Found");
        expect(wrapper.find('[data-description="loading message"]').exists()).toBe(false);
    });

    it("does not call the import failed when Galaxy only could not report its progress", async () => {
        importEndsIn("SUCCESS");
        server.use(
            http.get("/api/tasks/{task_id}/state", ({ response }) =>
                response("5XX").json({ err_msg: "Bad Gateway", err_code: 502 }, { status: 502 }),
            ),
        );
        const wrapper = await importLink("https://usegalaxy.org/api/short_term_storage/abc");
        await vi.waitFor(() => expect(wrapper.text()).toContain("could not check how the import is going"));
        expect(wrapper.text()).not.toContain("may have expired");
    });
});
