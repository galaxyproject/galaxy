import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";

import { useServerMock } from "@/api/client/__mocks__";
import { type BrowsableFilesSourcePlugin, type CreatedEntry } from "@/api/remoteFiles";

import ExportRDMForm from "./ExportRDMForm.vue";
import FilesInput from "@/components/FilesDialog/FilesInput.vue";

const localVue = getLocalVue(true);

const CREATE_RECORD_BTN = "#create-record-button";
const EXPORT_TO_NEW_RECORD_BTN = "#export-button-new-record";
const EXPORT_TO_EXISTING_RECORD_BTN = "#export-button-existing-record";

const FAKE_RDM_SOURCE_URI = "gxfiles://test-uri";
const FAKE_RDM_EXISTING_RECORD_URI = "gxfiles://test-uri/test-record";
const FAKE_RECORD_NAME = "test record name";
const FAKE_ENTRY: CreatedEntry = {
    uri: FAKE_RDM_SOURCE_URI,
    name: FAKE_RECORD_NAME,
    external_link: "http://example.com",
};

const { server, http } = useServerMock();

async function initWrapper(fileSource?: BrowsableFilesSourcePlugin) {
    server.use(
        http.post("/api/remote_files", ({ response }) => {
            return response(200).json(FAKE_ENTRY);
        })
    );

    const wrapper = mount(ExportRDMForm as object, {
        propsData: {
            fileSource,
        },
        localVue,
    });
    await flushPromises();
    return wrapper;
}

describe("ExportRDMForm", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(async () => {
        wrapper = await initWrapper();
    });

    describe("Export to new record", () => {
        beforeEach(async () => {
            await selectExportChoice("new");
        });

        it("enables the create new record button when the required fields are filled in", async () => {
            expect(wrapper.find(CREATE_RECORD_BTN).attributes("disabled")).toBeTruthy();

            await setRecordNameInput(FAKE_RECORD_NAME);
            await setRDMSourceInput(FAKE_RDM_SOURCE_URI);

            expect(wrapper.find(CREATE_RECORD_BTN).attributes("disabled")).toBeFalsy();
        });

        it("displays the export to this record button when the create new record button is clicked", async () => {
            expect(wrapper.find(EXPORT_TO_NEW_RECORD_BTN).exists()).toBeFalsy();

            await setRecordNameInput(FAKE_RECORD_NAME);
            await setRDMSourceInput(FAKE_RDM_SOURCE_URI);
            await clickCreateNewRecordButton();

            expect(wrapper.find(EXPORT_TO_NEW_RECORD_BTN).exists()).toBeTruthy();
        });

        it("emits an export event when the export to new record button is clicked", async () => {
            await setFileNameInput("test file name");
            await setRecordNameInput(FAKE_RECORD_NAME);
            await setRDMSourceInput(FAKE_RDM_SOURCE_URI);
            await clickCreateNewRecordButton();

            await wrapper.find(EXPORT_TO_NEW_RECORD_BTN).trigger("click");
            expect(wrapper.emitted("export")).toBeTruthy();
        });
    });

    describe("Export to existing record", () => {
        beforeEach(async () => {
            await selectExportChoice("existing");
        });

        it("enables the export to existing record button when the required fields are filled in", async () => {
            expect(wrapper.find(EXPORT_TO_EXISTING_RECORD_BTN).attributes("disabled")).toBeTruthy();

            await setFileNameInput("test file name");
            await setRDMDirectoryInput(FAKE_RDM_EXISTING_RECORD_URI);

            expect(wrapper.find(EXPORT_TO_EXISTING_RECORD_BTN).attributes("disabled")).toBeFalsy();
        });

        it("emits an export event when the export to existing record button is clicked", async () => {
            await setFileNameInput("test file name");
            await setRDMDirectoryInput(FAKE_RDM_EXISTING_RECORD_URI);
            await wrapper.find(EXPORT_TO_EXISTING_RECORD_BTN).trigger("click");
            expect(wrapper.emitted("export")).toBeTruthy();
        });
    });

    describe("Pre-select specific File Source", () => {
        beforeEach(async () => {
            const specificFileSource: BrowsableFilesSourcePlugin = {
                id: "test-file-source",
                label: "Test File Source",
                doc: "Test File Source Description",
                uri_root: "gxfiles://test-file-source",
                writable: true,
                browsable: true,
                type: "rdm",
                supports: {
                    pagination: false,
                    search: false,
                    sorting: false,
                },
            };
            wrapper = await initWrapper(specificFileSource);
        });

        it("enables the create new record button only by setting the record name", async () => {
            await selectExportChoice("new", "test-file-source");
            expect(wrapper.find(CREATE_RECORD_BTN).attributes("disabled")).toBeTruthy();

            await setRecordNameInput(FAKE_RECORD_NAME);

            expect(wrapper.find(CREATE_RECORD_BTN).attributes("disabled")).toBeFalsy();
        });

        it("displays the export to this record button when the create new record button is clicked", async () => {
            await selectExportChoice("new", "test-file-source");
            expect(wrapper.find(EXPORT_TO_NEW_RECORD_BTN).exists()).toBeFalsy();

            await setRecordNameInput(FAKE_RECORD_NAME);
            await clickCreateNewRecordButton();

            expect(wrapper.find(EXPORT_TO_NEW_RECORD_BTN).exists()).toBeTruthy();
        });

        it("emits an export event when the export to new record button is clicked", async () => {
            await selectExportChoice("new", "test-file-source");
            await setFileNameInput("test file name");
            await setRecordNameInput(FAKE_RECORD_NAME);
            await clickCreateNewRecordButton();

            await wrapper.find(EXPORT_TO_NEW_RECORD_BTN).trigger("click");
            expect(wrapper.emitted("export")).toBeTruthy();
        });
    });

    async function selectExportChoice(choice: string, fileSourceId?: string) {
        const suffix = fileSourceId ? `${fileSourceId}` : "any";
        const exportChoice = wrapper.find(`#radio-${choice}-${suffix}`);
        await exportChoice.setChecked(true);
    }

    async function setRDMSourceInput(newValue: string) {
        const component = wrapper.findComponent(FilesInput);
        expect(component.attributes("placeholder")).toContain("source");
        component.vm.$emit("input", newValue);
        await flushPromises();
    }

    async function setRDMDirectoryInput(newValue: string) {
        const component = wrapper.findComponent(FilesInput);
        expect(component.attributes("placeholder")).toContain("directory");
        component.vm.$emit("input", newValue);
        await flushPromises();
    }

    async function setRecordNameInput(newValue: string) {
        const recordNameInput = wrapper.find("#record-name-input");
        await recordNameInput.setValue(newValue);
    }

    async function setFileNameInput(newValue: string) {
        const recordNameInput = wrapper.find("#file-name-input");
        await recordNameInput.setValue(newValue);
    }

    async function clickCreateNewRecordButton() {
        const createRecordButton = wrapper.find(CREATE_RECORD_BTN);
        expect(createRecordButton.attributes("disabled")).toBeFalsy();
        await createRecordButton.trigger("click");
        await flushPromises();
    }
});
