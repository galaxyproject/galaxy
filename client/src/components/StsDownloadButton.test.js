import "jest-location-mock";

import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
import { setupMockConfig } from "tests/jest/mockConfig";

import StsDownloadButton from "./StsDownloadButton.vue";

const localVue = getLocalVue();
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
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(async () => {
        axiosMock.reset();
    });

    it("should fallback to a URL if tasks not enabled", async () => {
        const windowSpy = jest.spyOn(window, "open");
        windowSpy.mockImplementation(() => {});
        const wrapper = await mountStsDownloadButtonWrapper(NO_TASKS_CONFIG);
        wrapper.vm.onDownload(NO_TASKS_CONFIG);
        await flushPromises();
        expect(window.open).toHaveBeenCalled();
    });

    it("should poll until ready", async () => {
        axiosMock.onPost(DOWNLOAD_ENDPOINT).reply(200, { storage_request_id: STORAGE_REQUEST_ID });
        const wrapper = await mountStsDownloadButtonWrapper(TASKS_CONFIG);
        axiosMock.onGet(`api/short_term_storage/${STORAGE_REQUEST_ID}/ready`).reply(200, true);

        wrapper.vm.onDownload(TASKS_CONFIG);
        await flushPromises();
        expect(window.location).toBeAt(`api/short_term_storage/${STORAGE_REQUEST_ID}`);
    });

    it("should be in a waiting state while polling", async () => {
        axiosMock.onPost(DOWNLOAD_ENDPOINT).reply(200, { storage_request_id: STORAGE_REQUEST_ID });
        const wrapper = await mountStsDownloadButtonWrapper(TASKS_CONFIG);
        axiosMock.onGet(`api/short_term_storage/${STORAGE_REQUEST_ID}/ready`).reply(200, false);

        expect(wrapper.vm.waiting).toBeFalsy();
        wrapper.vm.onDownload(TASKS_CONFIG);
        await flushPromises();
        expect(wrapper.vm.waiting).toBeTruthy();
    });
});
