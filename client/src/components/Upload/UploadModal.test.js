import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import UploadModal from "./UploadModal.vue";
import store from "../../store";
import { shallowMount, createLocalVue } from "@vue/test-utils";
import BootstrapVue from "bootstrap-vue";

jest.mock("app");
jest.mock("../History/caching");

const propsData = {
    chunkUploadSize: 1024,
    uploadPath: "/api/tools",
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

        const localVue = createLocalVue();
        localVue.use(BootstrapVue);

        wrapper = await shallowMount(UploadModal, {
            store,
            propsData,
            localVue,
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
        expect(wrapper.vm.listExtensions.length).toBe(2);
        expect(wrapper.vm.listExtensions[0].id).toBe("auto");
        expect(wrapper.vm.listExtensions[1].id).toBe("fasta");
    });

    it("should fetch genomes and parse them", async () => {
        expect(wrapper.vm.listGenomes.length).toBe(3);
    });
});
