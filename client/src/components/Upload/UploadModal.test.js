import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { createPinia } from "pinia";
import { useHistoryStore } from "stores/historyStore";
import { useUserStore } from "stores/userStore";
import { getLocalVue } from "tests/jest/helpers";

import { getDatatypes, getGenomes } from "./services";
import UploadModal from "./UploadModal";
import UploadModalContent from "./UploadModalContent";

jest.mock("app");
jest.mock("./services");
jest.mock("@/schema");

jest.mock("@/composables/config", () => ({
    useConfig: jest.fn(() => ({
        config: {},
        isConfigLoaded: true,
    })),
}));

const fastaResponse = {
    description_url: "https://wiki.galaxyproject.org/Learn/Datatypes#Fasta",
    display_in_upload: true,
    extension: "fasta",
    description:
        "A sequence in FASTA format consists of a single-line description, followed by lines of sequence data. The first character of the description line is a greater-than ('>') symbol in the first column. All lines should be shorter than 80 characters.",
};

const genomesResponse = [
    ["Scarlet macaw Jun 2013 (SMACv1.1/araMac1) (araMac1)", "araMac1"],
    ["Cat Dec. 2008 (NHGRI/GTB V17e/felCat4) (felCat4)", "felCat4"],
    ["Cat Sep. 2011 (ICGSC Felis_catus 6.2/felCat5) (felCat5)", "felCat5"],
];

getDatatypes.mockReturnValue({ data: [fastaResponse] });
getGenomes.mockReturnValue({ data: genomesResponse });

const propsData = {
    chunkUploadSize: 1024,
    uploadPath: "/api/tools",
    fileSourcesConfigured: true,
};

describe("UploadModal.vue", () => {
    let wrapper;
    let axiosMock;
    let userStore;
    let historyStore;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(`/api/histories/count`).reply(200, 0);

        const localVue = getLocalVue();
        const pinia = createPinia();

        wrapper = mount(UploadModal, {
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
            pinia,
        });

        userStore = useUserStore();
        userStore.currentUser = { id: "fakeUser" };
        historyStore = useHistoryStore();
        historyStore.setHistories([{ id: "fakeHistory" }]);
        historyStore.setCurrentHistoryId("fakeHistory");

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
