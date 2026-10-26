import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";

import HistoryDatasetPicker from "./HistoryDatasetPicker.vue";

const localVue = getLocalVue();

const { server, http } = useServerMock();

describe("HistoryDatasetPicker", () => {
    it("lists the most recently updated histories first by default", async () => {
        const historyRequests: URLSearchParams[] = [];
        server.use(
            http.get("/api/histories", ({ request, response }) => {
                historyRequests.push(new URL(request.url).searchParams);
                return response(200).json([]);
            }),
        );

        mount(HistoryDatasetPicker as object, {
            localVue,
            pinia: createTestingPinia(),
            attachTo: document.body,
        });
        await flushPromises();

        expect(historyRequests.length).toBeGreaterThan(0);
        const params = historyRequests[historyRequests.length - 1]!;
        expect(params.get("sort_by")).toBe("update_time");
        expect(params.get("sort_desc")).toBe("true");
    });
});
