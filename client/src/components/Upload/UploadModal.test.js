import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import UploadModal from "./UploadModal";
import UploadModalContent from "./UploadModalContent";
import store from "../../store";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";

import MockCurrentUser from "../providers/MockCurrentUser";
import MockCurrentHistory from "../providers/MockCurrentHistory";

jest.mock("app");

const propsData = {
    chunkUploadSize: 1024,
    uploadPath: "/api/tools",
    fileSourcesConfigured: true,
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

        wrapper = await mount(UploadModal, {
            store,
            propsData,
            localVue,
            stubs: {
                // Need to stub all this horrible-ness because of the last 2 tests
                // which need to dig into the first layer of the mount tree, will remove
                // all of this shortly with a PR that completely replaces Upload
                CurrentUser: MockCurrentUser({ id: "fakeuser" }),
                UserHistories: MockCurrentHistory({ id: "fakehistory" }),
                BTabs: true,
                BTab: true,
                Collection: true,
                Composite: true,
                Default: true,
                RulesInput: true,
            },
        });
    });

    afterEach(() => {
        axiosMock.restore();
        axiosMock.reset();
    });

    it("should load with correct defaults", async () => {
        expect(wrapper.vm.auto.id).toBe("auto");
        expect(wrapper.vm.datatypesDisableAuto).toBe(false);
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
