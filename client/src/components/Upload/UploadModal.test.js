import "tests/jest/mockHelpPopovers";

import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import UploadContainer from "./UploadContainer.vue";
import UploadModal from "./UploadModal.vue";

jest.mock("@/composables/config", () => ({
    useConfig: jest.fn(() => ({
        config: {},
        isConfigLoaded: true,
    })),
}));

const { server, http } = useServerMock();

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

const propsData = {
    chunkUploadSize: 1024,
    fileSourcesConfigured: true,
};

describe("UploadModal.vue", () => {
    let wrapper;
    let userStore;
    let historyStore;

    beforeEach(async () => {
        server.use(
            http.get("/api/datatypes", ({ response }) => {
                return response(200).json([fastaResponse]);
            }),

            http.get("/api/genomes", ({ response }) => {
                return response(200).json(genomesResponse);
            }),

            http.get("/api/histories/count", ({ response }) => {
                return response(200).json(0);
            })
        );

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

    it("should load with correct defaults", async () => {
        const contentWrapper = wrapper.findComponent(UploadContainer);
        expect(contentWrapper.vm.auto.id).toBe("auto");
        expect(contentWrapper.vm.datatypesDisableAuto).toBe(false);
    });

    it("should fetch datatypes and parse them", async () => {
        const contentWrapper = wrapper.findComponent(UploadContainer);
        expect(contentWrapper.exists()).toBe(true);
        expect(contentWrapper.vm.listExtensions.length).toBe(2);
        expect(contentWrapper.vm.listExtensions[0].id).toBe("auto");
        expect(contentWrapper.vm.listExtensions[1].id).toBe("fasta");
    });

    it("should fetch genomes and parse them", async () => {
        const contentWrapper = wrapper.findComponent(UploadContainer);
        expect(contentWrapper.vm.listDbKeys.length).toBe(3);
    });
});
