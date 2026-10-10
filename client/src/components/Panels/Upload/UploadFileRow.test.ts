import { createTestingPinia } from "@pinia/testing";
import { getFakeHistorySummary } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { makeUrlItem, withUploadState } from "@/composables/upload/testHelpers/uploadFixtures";
import { seedCurrentHistory } from "@/stores/testUtils";

import UploadFileRow from "./UploadFileRow.vue";
import CopyToClipboard from "@/components/CopyToClipboard.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

server.use(http.get("/api/configuration", ({ response }) => response(200).json({})));

describe("UploadFileRow source URL", () => {
    it("renders the source URL from the item display info", () => {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        seedCurrentHistory(getFakeHistorySummary({ id: "hist-a", name: "History A" }), pinia);

        const wrapper = mount(UploadFileRow, {
            props: { file: withUploadState(makeUrlItem()) },
            global: {
                ...withPlugins(localVue, pinia),
                stubs: {
                    ...localVue.stubs,
                    CopyToClipboard: true,
                    FontAwesomeIcon: true,
                    SwitchToHistoryLink: true,
                    UtcDate: true,
                },
            },
        });

        const url = wrapper.find(".source-url-text");
        expect(url.exists()).toBe(true);
        expect(url.text()).toContain("http://example.com/file.txt");
        expect(url.attributes("title")).toBe("http://example.com/file.txt");

        const copyIcon = wrapper.findComponent(CopyToClipboard);
        expect(copyIcon.exists()).toBe(true);
        expect(copyIcon.props("text")).toBe("http://example.com/file.txt");
    });
});
