import { createTestingPinia } from "@pinia/testing";
import DATA from "@tests/test-data/paired-collection-creator.data.js";
import { mount, shallowMount } from "@vue/test-utils";
import PairedListCollectionCreator from "components/Collections/PairedListCollectionCreator";
import flushPromises from "flush-promises";
import Vue from "vue";

import { useServerMock } from "@/api/client/__mocks__";

// Mock the localize directive
// (otherwise we get: [Vue warn]: Failed to resolve directive: localize)
Vue.directive("localize", {
    bind(el, binding) {
        el.textContent = binding.value;
    },
});

const { server, http } = useServerMock();

describe("PairedListCollectionCreator", () => {
    let wrapper;
    const pinia = createTestingPinia();

    beforeEach(() => {
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response(200).json({
                    chunk_upload_size: 100,
                    file_sources_configured: true,
                });
            })
        );
    });

    it("performs an autopair on startup if we have a selection", async () => {
        // Kind of deprecated because we are never using `props.fromSelection: true` anywhere

        wrapper = shallowMount(PairedListCollectionCreator, {
            propsData: {
                historyId: "history_id",
                initialElements: DATA._1,
                fromSelection: true,
            },
            pinia,
        });

        await flushPromises();
        // Autopair is called on startup
        const pairsCountDisplay = wrapper.find('[data-description="number of pairs"]');
        expect(pairsCountDisplay.text()).toContain(`${DATA._1.length / 2} pairs`);
    });

    it("selects the correct name for an autopair", async () => {
        wrapper = mount(PairedListCollectionCreator, {
            propsData: {
                historyId: "history_id",
                initialElements: DATA._2,
            },
            pinia,
            stubs: {
                FontAwesomeIcon: true,
                BPopover: true,
            },
        });

        await flushPromises();
        //change filter to .1.fastq/.2.fastq
        await wrapper.find("div.forward-unpaired-filter > div.input-group-append > button").trigger("click");
        await wrapper
            .findAll("div.dropdown-menu > a.dropdown-item")
            .wrappers.find((e) => e.text() == ".1.fastq")
            .trigger("click");
        //assert forward filter
        const forwardFilter = wrapper.find("div.forward-unpaired-filter > input").element.value;
        expect(forwardFilter).toBe(".1.fastq");
        //assert reverse filter
        const reverseFilter = wrapper.find("div.reverse-unpaired-filter > input").element.value;
        expect(reverseFilter).toBe(".2.fastq");
        // click Autopair
        await wrapper.find(".autopair-link").trigger("click");
        //assert pair-name longer name
        const pairname = wrapper.find("span.pair-name");
        expect(pairname.text()).toBe("DP134_1_FS_PSII_FSB_42C_A10");
    });

    it("removes the period from autopair name", async () => {
        wrapper = mount(PairedListCollectionCreator, {
            propsData: {
                historyId: "history_id",
                initialElements: DATA._3,
            },
            pinia,
            stubs: {
                FontAwesomeIcon: true,
                BPopover: true,
            },
        });

        await flushPromises();
        //change filter to .1.fastq/.2.fastq
        await wrapper.find("div.forward-unpaired-filter > div.input-group-append > button").trigger("click");
        await wrapper
            .findAll("div.dropdown-menu > a.dropdown-item")
            .wrappers.find((e) => e.text() == ".1.fastq")
            .trigger("click");
        //assert forward filter
        const forwardFilter = wrapper.find("div.forward-unpaired-filter > input").element.value;
        expect(forwardFilter).toBe(".1.fastq");
        //assert reverse filter
        const reverseFilter = wrapper.find("div.reverse-unpaired-filter > input").element.value;
        expect(reverseFilter).toBe(".2.fastq");
        // click Autopair
        await wrapper.find(".autopair-link").trigger("click");
        //assert pair-name longer name
        const pairname = wrapper.find("span.pair-name");
        expect(pairname.text()).toBe("UII_moo_1");
    });

    it("autopairs correctly when filters are typed in", async () => {
        wrapper = mount(PairedListCollectionCreator, {
            propsData: {
                historyId: "history_id",
                initialElements: DATA._4,
            },
            pinia,
            stubs: {
                FontAwesomeIcon: true,
                BPopover: true,
            },
        });

        await flushPromises();
        //change filter to _R1/_R2
        await wrapper.find("div.forward-unpaired-filter > input").setValue("_R1");
        await wrapper.find("div.reverse-unpaired-filter > input").setValue("_R2");
        //assert forward filter
        const forwardFilter = wrapper.find("div.forward-unpaired-filter > input").element.value;
        expect(forwardFilter).toBe("_R1");
        //assert reverse filter
        const reverseFilter = wrapper.find("div.reverse-unpaired-filter > input").element.value;
        expect(reverseFilter).toBe("_R2");
        // click Autopair
        await wrapper.find(".autopair-link").trigger("click");
        //assert all pairs matched
        expect(wrapper.findAll("li.dataset unpaired").length == 0).toBeTruthy();
    });
});
