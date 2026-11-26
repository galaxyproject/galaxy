import { createTestRouter, getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import LibraryFolder from "./LibraryFolder.vue";

vi.mock("./services", () => ({
    Services: class {
        getFolderContents() {
            return Promise.resolve({
                folder_contents: [{ id: "dataset_id", type: "file", name: "reads.fastq", deleted: false }],
                metadata: { can_add_library_item: true, total_rows: 1, full_path: [] },
            });
        }
    },
}));

const localVue = getLocalVue();
const routes = [
    { path: "/libraries/folders/:folder_id", name: "LibraryFolder", component: {} },
    { path: "/libraries/folders/:folder_id/dataset/:dataset_id", name: "LibraryDataset", component: {} },
];

async function mountLibraryFolder() {
    const wrapper = mount(LibraryFolder as object, {
        props: { folder_id: "folder_id" },
        global: {
            ...withPlugins(localVue, createTestRouter(routes)),
            stubs: { ...localVue.stubs, FolderTopBar: true },
        },
    });
    await flushPromises();
    return wrapper;
}

function rowCheckboxNames(wrapper: ReturnType<typeof mount>) {
    return wrapper.findAll("tbody input[type='checkbox']").map((box) => box.attributes("aria-label"));
}

describe("LibraryFolder", () => {
    it("names each row's selection checkbox after the row", async () => {
        const wrapper = await mountLibraryFolder();

        expect(rowCheckboxNames(wrapper)).toEqual(["Select reads.fastq"]);
    });

    it("gives a new, still unnamed folder row a generic selection checkbox name", async () => {
        const wrapper = await mountLibraryFolder();

        (wrapper.vm as unknown as { newFolder: () => void }).newFolder();
        await flushPromises();

        expect(rowCheckboxNames(wrapper)).toEqual(["Select for bulk actions", "Select reads.fastq"]);
    });
});
