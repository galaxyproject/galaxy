import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import type { JobExportHistoryArchiveModel } from "@/api/histories.export";
import { copy } from "@/utils/clipboard";

import ExportLink from "./ExportLink.vue";

vi.mock("@/utils/clipboard", () => ({ copy: vi.fn() }));

const EXPORT_URL = "https://galaxy.example/history/export_archive?id=1";

describe("ExportLink", () => {
    it("copies the export URL when the link icon is clicked", async () => {
        const wrapper = shallowMount(ExportLink as object, {
            props: {
                historyExport: { external_download_permanent_url: EXPORT_URL } as JobExportHistoryArchiveModel,
            },
            global: { ...getLocalVue(), renderStubDefaultSlot: true, stubs: { FontAwesomeIcon: false } },
        });
        await wrapper.find("svg.copy-export-link").trigger("click");
        expect(copy).toHaveBeenCalledWith(EXPORT_URL, "Export URL copied to your clipboard");
    });
});
