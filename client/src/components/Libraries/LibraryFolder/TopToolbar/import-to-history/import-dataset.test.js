import axios from "axios";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import mod_import_dataset from "./import-dataset";

vi.mock("axios", () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
    },
}));

describe("ImportDatasetModal", () => {
    beforeEach(() => {
        axios.get.mockImplementation(async (url) =>
            url.endsWith("api/histories") ? { data: [{ id: "history1", name: "History 1" }] } : { data: {} },
        );
        axios.post.mockImplementation((url) =>
            url.endsWith("api/histories")
                ? Promise.resolve({ data: { id: "history2", name: "New History" } })
                : new Promise(() => {}),
        );
    });

    function importButton() {
        return [...document.querySelectorAll(".ui-modal .buttons button")].find((b) => b.textContent === "Import");
    }

    it("keeps Import disabled while importing into an existing history", async () => {
        new mod_import_dataset.ImportDatasetModal({ selected: { dataset_ids: ["dataset1"], folder_ids: [] } });
        await flushPromises();
        importButton().click();
        await flushPromises();
        expect(document.querySelector(".ui-modal .progress-bar-import")).not.toBeNull();
        expect(importButton().disabled).toBe(true);
    });

    it("keeps Import disabled while importing into a new history", async () => {
        new mod_import_dataset.ImportDatasetModal({ selected: { dataset_ids: ["dataset1"], folder_ids: [] } });
        await flushPromises();
        document.querySelector('.ui-modal input[name="history_name"]').value = "New History";
        importButton().click();
        await flushPromises();
        expect(document.querySelector(".ui-modal .progress-bar-import")).not.toBeNull();
        expect(importButton().disabled).toBe(true);
    });
});
