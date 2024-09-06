import { shallowMount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { type InvocationExportPlugin } from "@/components/Workflow/Invocation/Export/Plugins";

import InvocationExportPluginCard from "./InvocationExportPluginCard.vue";

const localVue = getLocalVue();

const FAKE_INVOCATION_ID = "fake-invocation-id";
const FAKE_EXPORT_PLUGIN: InvocationExportPlugin = {
    id: "fake-plugin-id",
    title: "Plugin Title",
    markdownDescription: `some **markdown** description`,
    exportParams: {
        modelStoreFormat: "tgz",
        includeFiles: false,
        includeDeleted: false,
        includeHidden: false,
    },
    additionalActions: [
        {
            id: "fake-action-1",
            title: "Fake export action 1",
            run: jest.fn(),
        },
        {
            id: "fake-action-2",
            title: "Fake export action 2",
            run: jest.fn(),
        },
    ],
};

describe("InvocationExportPluginCard", () => {
    let wrapper: any;
    let axiosMock: MockAdapter;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        wrapper = shallowMount(InvocationExportPluginCard as object, {
            propsData: { exportPlugin: FAKE_EXPORT_PLUGIN, invocationId: FAKE_INVOCATION_ID },
            localVue,
        });
        await flushPromises();
    });

    afterEach(async () => {
        axiosMock.reset();
    });

    it("should display the plugin's title", () => {
        const title = wrapper.find(".export-plugin-title");
        expect(title.exists()).toBeTruthy();
        expect(title.text()).toBe("Plugin Title");
    });

    it("should render the plugin's description as markdown", () => {
        const description = wrapper.find(".markdown-description");
        expect(description.exists()).toBeTruthy();
        expect(description.html()).toContain("<strong>markdown</strong>");
    });

    it("should have a direct download button", () => {
        const downloadButton = wrapper.find(".download-button");
        expect(downloadButton.exists()).toBeTruthy();
    });

    it("should have an export to remote file source button", () => {
        const remoteExportButton = wrapper.find(".remote-export-button");
        expect(remoteExportButton.exists()).toBeTruthy();
    });

    it("should display a button for each additional action", () => {
        const actionButtons = wrapper.findAll(".action-button");
        expect(actionButtons.length).toBe(FAKE_EXPORT_PLUGIN.additionalActions.length);
    });
});
