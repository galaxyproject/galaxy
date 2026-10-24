import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import FtpUploadHelp from "./FtpUploadHelp.vue";

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({ config: {}, isConfigLoaded: true })),
}));

describe("FtpUploadHelp", () => {
    it("skips the log in sentence without an FTP site", () => {
        const wrapper = mount(FtpUploadHelp as object, { propsData: { uri: "gxftp://" }, localVue: getLocalVue() });
        const text = wrapper.find("[data-description='ftp upload help']").text();
        expect(text).toContain("upload files via FTP");
        expect(text).not.toContain("log in to the FTP server");
    });
});
