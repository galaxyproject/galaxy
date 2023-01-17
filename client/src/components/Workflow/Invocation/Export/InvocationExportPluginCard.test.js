import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import flushPromises from "flush-promises";
import InvocationExportPluginCard from "./InvocationExportPluginCard.vue";
import { InvocationExportPlugin, InvocationExportPluginAction } from "./model";

const localVue = getLocalVue();

const FAKE_INVOCATION_ID = "fake-invocation-id";
const FAKE_EXPORT_PLUGIN = new InvocationExportPlugin({
    title: "Plugin Title",
    markdownDescription: `some **markdown** description`,
    exportParams: {
        modelStoreFormat: "tgz",
        includeFiles: false,
        includeDeleted: false,
        includeHidden: false,
    },
    additionalActions: [
        new InvocationExportPluginAction({
            id: "fake-action-1",
            title: "Fake export action 1",
        }),
        new InvocationExportPluginAction({
            id: "fake-action-2",
            title: "Fake export action 2",
        }),
    ],
});

describe("InvocationExportPluginCard", () => {
    let wrapper;
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        wrapper = shallowMount(InvocationExportPluginCard, {
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

    it("should generate the expected download URL for the invocation", () => {
        const downloadButton = wrapper.find(".download-button");
        expect(downloadButton.attributes("downloadendpoint")).toBe(
            `/api/invocations/${FAKE_INVOCATION_ID}/prepare_store_download`
        );
    });

    it("should display a button for each additional action", () => {
        const actionButtons = wrapper.findAll(".action-button");
        expect(actionButtons.length).toBe(FAKE_EXPORT_PLUGIN.additionalActions.length);
    });
});
