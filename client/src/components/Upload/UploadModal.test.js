import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import UploadModal from "./UploadModal.vue";
import { setupTestGalaxy } from "qunit/test-app";

import { shallowMount, createLocalVue } from "@vue/test-utils";

const propsData = {
    chunkUploadSize: 1024,
    uploadPath: "/api/tools",
};

describe("UploadModal.vue", () => {
    let wrapper;
    let localVue;
    let axiosMock;

    beforeEach(() => {
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

        localVue = createLocalVue();
        setupTestGalaxy();
        wrapper = shallowMount(UploadModal, {
            propsData: propsData,
            localVue: localVue,
        });
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("should load with correct defaults", async () => {
        expect(wrapper.vm.auto.id).to.equals("auto");
        expect(wrapper.vm.datatypesDisableAuto).to.equals(false);
    });

    it("should fetch datatypes and parse them", async () => {
        await localVue.nextTick();
        await localVue.nextTick();
        expect(wrapper.vm.listExtensions.length).to.equals(2);
        expect(wrapper.vm.listExtensions[0].id).to.equals("auto");
        expect(wrapper.vm.listExtensions[1].id).to.equals("fasta");
    });

    it("should fetch genomes and parse them", async () => {
        await localVue.nextTick();
        await localVue.nextTick();
        expect(wrapper.vm.listGenomes.length).to.equals(3);
    });
});
