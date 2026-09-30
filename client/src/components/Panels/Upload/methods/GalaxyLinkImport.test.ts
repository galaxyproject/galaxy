import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import GalaxyLinkImport from "./GalaxyLinkImport.vue";

const IMPORT = "/api/histories/{history_id}/contents_from_store";

const { server, http } = useServerMock();

async function importLink(link: string) {
    const wrapper = mount(GalaxyLinkImport as object, {
        localVue: getLocalVue(),
        propsData: { method: { id: "galaxy-link" }, targetHistoryId: "hist_1" },
    });
    await wrapper.find('[data-description="galaxy link input"]').setValue(link);
    await wrapper.find('[data-description="galaxy link import"]').trigger("click");
    return wrapper;
}

describe("GalaxyLinkImport", () => {
    it("sends the trimmed link and says what was imported", async () => {
        let body: Record<string, unknown> = {};
        server.use(
            http.post(IMPORT, async ({ request, response }) => {
                body = await request.json();
                return response(200).json([{ name: "sample1" }] as never);
            }),
        );
        const wrapper = await importLink("  https://usegalaxy.org/api/short_term_storage/abc\n");
        await vi.waitFor(() => expect(wrapper.text()).toContain("Imported sample1"));
        expect(body).toMatchObject({
            store_content_uri: "https://usegalaxy.org/api/short_term_storage/abc",
            model_store_format: "tar.gz",
            discarded_data: "forbid",
        });
    });

    it("shows the reason Galaxy gives", async () => {
        server.use(
            http.post(IMPORT, ({ response }) =>
                response("4XX").json({ err_msg: "History is not accessible", err_code: 403 }, { status: 403 }),
            ),
        );
        const wrapper = await importLink("https://usegalaxy.org/api/short_term_storage/abc");
        await vi.waitFor(() => expect(wrapper.text()).toContain("History is not accessible"));
    });

    it("explains a link that could not be fetched", async () => {
        // The other Galaxy answering 404 for an expired link reaches this one as a bare 500.
        server.use(http.post(IMPORT, () => new HttpResponse("Internal Server Error" as never, { status: 500 })));
        const wrapper = await importLink("https://usegalaxy.org/api/short_term_storage/old");
        await vi.waitFor(() => expect(wrapper.text()).toContain("may have expired"));
    });

    it("stops waiting when the request itself fails", async () => {
        server.use(http.post(IMPORT, () => HttpResponse.error()));
        const wrapper = await importLink("https://usegalaxy.org/api/short_term_storage/abc");
        await vi.waitFor(() => expect(wrapper.text()).toContain("may have expired"));
        expect(wrapper.text()).not.toContain("Importing...");
    });
});
