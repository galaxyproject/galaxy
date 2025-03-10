import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";

import { useServerMock } from "@/api/client/__mocks__";
import { type BrowsableFilesSourcePlugin, type CreatedEntry } from "@/api/remoteFiles";

import RDMDestinationSelector from "./RDMDestinationSelector.vue";
import FilesInput from "@/components/FilesDialog/FilesInput.vue";

const localVue = getLocalVue(true);

const CREATE_RECORD_BTN = "#create-record-button";

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

    const wrapper = mount(RDMDestinationSelector as object, {
        propsData: {
            fileSource,
        },
        localVue,
    });
    await flushPromises();
    return wrapper;
}

describe("RDMDestinationSelector", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(async () => {
        wrapper = await initWrapper();
    });

    describe("Select new record", () => {
        beforeEach(async () => {
            await selectExportChoice("new");
        });

        it("enables the create new record button when the required fields are filled in", async () => {
            expect(wrapper.find(CREATE_RECORD_BTN).attributes("disabled")).toBeTruthy();

            await setRecordNameInput(FAKE_RECORD_NAME);
            await setRDMSourceInput(FAKE_RDM_SOURCE_URI);

            expect(wrapper.find(CREATE_RECORD_BTN).attributes("disabled")).toBeFalsy();
        });

        it("emits onRecordSelected when the create new record button is clicked", async () => {
            expect(wrapper.emitted("onRecordSelected")).toBeFalsy();

            await setRecordNameInput(FAKE_RECORD_NAME);
            await setRDMSourceInput(FAKE_RDM_SOURCE_URI);
            await clickCreateNewRecordButton();

            const emitted = wrapper.emitted("onRecordSelected");

            expect(emitted).toBeTruthy();
            expect(emitted?.at(0)[0]).toEqual(FAKE_ENTRY.uri);
        });
    });

    describe("Select existing record", () => {
        beforeEach(async () => {
            await selectExportChoice("existing");
        });

        it("emits onRecordSelected event when the existing record is selected", async () => {
            expect(wrapper.emitted("onRecordSelected")).toBeFalsy();

            await setRDMDirectoryInput(FAKE_RDM_EXISTING_RECORD_URI);

            const emitted = wrapper.emitted("onRecordSelected");
            expect(emitted).toBeTruthy();
            expect(emitted?.at(0)[0]).toEqual(FAKE_RDM_EXISTING_RECORD_URI);
        });
    });

    describe("Pre-select specific File Source", () => {
        const PRESELECTED_FILE_SOURCE_ID = "test-file-source";
        const PRESELECTED_FILE_SOURCE_URI = "gxfiles://preselected-file-source";

        beforeEach(async () => {
            const specificFileSource: BrowsableFilesSourcePlugin = {
                id: PRESELECTED_FILE_SOURCE_ID,
                label: "Test File Source",
                doc: "Test File Source Description",
                uri_root: PRESELECTED_FILE_SOURCE_URI,
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

        describe("Select new record", () => {
            beforeEach(async () => {
                await selectExportChoice("new", PRESELECTED_FILE_SOURCE_ID);
            });

            it("enables the create new record button only by setting the record name", async () => {
                expect(wrapper.find(CREATE_RECORD_BTN).attributes("disabled")).toBeTruthy();

                await setRecordNameInput(FAKE_RECORD_NAME);

                expect(wrapper.find(CREATE_RECORD_BTN).attributes("disabled")).toBeFalsy();
            });

            it("emits onRecordSelected event when the create new record button is clicked", async () => {
                expect(wrapper.emitted("onRecordSelected")).toBeFalsy();

                await setRecordNameInput(FAKE_RECORD_NAME);
                await clickCreateNewRecordButton();

                const emitted = wrapper.emitted("onRecordSelected");
                expect(emitted).toBeTruthy();
                expect(emitted?.at(0)[0]).toEqual(FAKE_ENTRY.uri);
            });
        });

        describe("Select existing record", () => {
            beforeEach(async () => {
                await selectExportChoice("existing", PRESELECTED_FILE_SOURCE_ID);
            });

            it("emits onRecordSelected event when the existing record is selected", async () => {
                expect(wrapper.emitted("onRecordSelected")).toBeFalsy();

                const fakeRecordUri = `${PRESELECTED_FILE_SOURCE_URI}/preselected-test-record`;
                await setRDMDirectoryInput(fakeRecordUri);

                const emitted = wrapper.emitted("onRecordSelected");
                expect(emitted).toBeTruthy();
                expect(emitted?.at(0)[0]).toEqual(fakeRecordUri);
            });
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

    async function clickCreateNewRecordButton() {
        const createRecordButton = wrapper.find(CREATE_RECORD_BTN);
        expect(createRecordButton.attributes("disabled")).toBeFalsy();
        await createRecordButton.trigger("click");
        await flushPromises();
    }
});
