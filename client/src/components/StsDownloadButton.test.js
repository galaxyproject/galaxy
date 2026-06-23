import { getLocalVue } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import StsDownloadButton from "./StsDownloadButton.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

const NO_TASKS_CONFIG = {
    enable_celery_tasks: false,
};
const TASKS_CONFIG = {
    enable_celery_tasks: true,
};
const FALLBACK_URL = "http://cow.com/direct_download";
const DOWNLOAD_ENDPOINT = "http://cow.com/prepare_download";
const STORAGE_REQUEST_ID = "moocow1235";

async function mountStsDownloadButtonWrapper(config) {
    setupMockConfig(config);

    const pinia = createPinia();
    const wrapper = mount(StsDownloadButton, {
        propsData: {
            title: "my title",
            fallbackUrl: FALLBACK_URL,
            downloadEndpoint: DOWNLOAD_ENDPOINT,
        },
        localVue,
        pinia,
    });
    await flushPromises();
    return wrapper;
}

describe("StsDownloadButton", () => {
    beforeEach(async () => {
        // Reset handlers before each test
    });

    it("should fallback to a URL if tasks not enabled", async () => {
        const windowSpy = vi.spyOn(window, "open");
        windowSpy.mockImplementation(() => {});
        const wrapper = await mountStsDownloadButtonWrapper(NO_TASKS_CONFIG);
        wrapper.vm.onDownload(NO_TASKS_CONFIG);
        await flushPromises();
        expect(window.open).toHaveBeenCalled();
    });

    it("should poll until ready", async () => {
        server.use(
            http.untyped.post(DOWNLOAD_ENDPOINT, () => {
                return HttpResponse.json({ storage_request_id: STORAGE_REQUEST_ID });
            }),
            http.untyped.get(`api/short_term_storage/${STORAGE_REQUEST_ID}/ready`, () => {
                return HttpResponse.json(true);
            }),
        );
        const wrapper = await mountStsDownloadButtonWrapper(TASKS_CONFIG);

        wrapper.vm.onDownload(TASKS_CONFIG);
        await flushPromises();
        expect(window.location).toBeAt(`api/short_term_storage/${STORAGE_REQUEST_ID}`);
    });

    it("should be in a waiting state while polling", async () => {
        server.use(
            http.untyped.post(DOWNLOAD_ENDPOINT, () => {
                return HttpResponse.json({ storage_request_id: STORAGE_REQUEST_ID });
            }),
            http.untyped.get(`api/short_term_storage/${STORAGE_REQUEST_ID}/ready`, () => {
                return HttpResponse.json(false);
            }),
        );
        const wrapper = await mountStsDownloadButtonWrapper(TASKS_CONFIG);

        expect(wrapper.vm.waiting).toBeFalsy();
        wrapper.vm.onDownload(TASKS_CONFIG);
        await flushPromises();
        expect(wrapper.vm.waiting).toBeTruthy();
    });
});
