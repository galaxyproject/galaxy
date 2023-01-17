import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import UploadModal from "./UploadModal";
import UploadModalContent from "./UploadModalContent";
import { mount } from "@vue/test-utils";
import { getLocalVue, mockModule } from "tests/jest/helpers";
import { userStore } from "store/userStore";
import { historyStore } from "store/historyStore";
import { configStore } from "store/configStore";
import Vuex from "vuex";

jest.mock("app");

const propsData = {
    chunkUploadSize: 1024,
    uploadPath: "/api/tools",
    fileSourcesConfigured: true,
};

const createStore = () => {
    return new Vuex.Store({
        modules: {
            user: mockModule(userStore, { currentUser: { id: "fakeuser" } }),
            history: mockModule(historyStore, { currentHistoryId: "fakehistory", histories: { fakehistory: {} } }),
            config: mockModule(configStore, { config: {} }),
        },
    });
};

describe("UploadModal.vue", () => {
    let wrapper;
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);

        const fastaResponse = {
            description_url: "https://wiki.galaxyproject.org/Learn/Datatypes#Fasta",
            display_in_upload: true,
            extension: "fasta",
            description:
                "A sequence in FASTA format consists of a single-line description, followed by lines of sequence data. The first character of the description line is a greater-than ('>') symbol in the first column. All lines should be shorter than 80 characters.",
        };
        const datatypesResponse = [fastaResponse];

        axiosMock.onGet(`/api/datatypes?extension_only=False`).reply(200, datatypesResponse);

        const genomesResponse = [
            ["Scarlet macaw Jun 2013 (SMACv1.1/araMac1) (araMac1)", "araMac1"],
            ["Cat Dec. 2008 (NHGRI/GTB V17e/felCat4) (felCat4)", "felCat4"],
            ["Cat Sep. 2011 (ICGSC Felis_catus 6.2/felCat5) (felCat5)", "felCat5"],
        ];
        axiosMock.onGet(`/api/genomes`).reply(200, genomesResponse);

        // mock current user & history

        axiosMock.onGet(`/api/datatypes?extension_only=False`).reply(200, datatypesResponse);

        const localVue = getLocalVue();
        const store = createStore();

        wrapper = await mount(UploadModal, {
            store,
            provide: { store },
            propsData,
            localVue,
            stubs: {
                BTabs: true,
                BTab: true,
                Collection: true,
                Composite: true,
                Default: true,
                RulesInput: true,
            },
        });

        await wrapper.vm.open();
    });

    afterEach(() => {
        axiosMock.restore();
        axiosMock.reset();
    });

    it("should load with correct defaults", async () => {
        const contentWrapper = wrapper.findComponent(UploadModalContent);
        expect(contentWrapper.vm.auto.id).toBe("auto");
        expect(contentWrapper.vm.datatypesDisableAuto).toBe(false);
    });

    it("should fetch datatypes and parse them", async () => {
        // lists are one layer deeper now, it won't matter after refactoring
        const contentWrapper = wrapper.findComponent(UploadModalContent);
        expect(contentWrapper.exists()).toBe(true);
        expect(contentWrapper.vm.listExtensions.length).toBe(2);
        expect(contentWrapper.vm.listExtensions[0].id).toBe("auto");
        expect(contentWrapper.vm.listExtensions[1].id).toBe("fasta");
    });

    it("should fetch genomes and parse them", async () => {
        // lists are one yaer deeper now, it won't matter after refactoring
        const contentWrapper = wrapper.findComponent(UploadModalContent);
        expect(contentWrapper.vm.listGenomes.length).toBe(3);
    });
});
