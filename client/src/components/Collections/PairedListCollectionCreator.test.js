import { mount } from "@vue/test-utils";
import { shallowMount } from "@vue/test-utils";
import PairedListCollectionCreator from "components/Collections/PairedListCollectionCreator";
import DATA from "../../../tests/qunit/test-data/paired-collection-creator.data.js";

describe("PairedListCollectionCreator", () => {
    let wrapper;

    it("autopairs the dataset", async () => {
        wrapper = shallowMount(PairedListCollectionCreator, {
            propsData: {
                initialElements: DATA._1,
                creationFn: () => {
                    return;
                },
                oncreate: () => {
                    return;
                },
                oncancel: () => {
                    return;
                },
                hideSourceItems: false,
            },
        });
        await wrapper.vm.$nextTick();
        // Autopair is called on startup
        expect(wrapper.findAll("li.dataset unpaired").length == 0).toBeTruthy();
    });

    it("selects the correct name for an auotpair", async () => {
        wrapper = mount(PairedListCollectionCreator, {
            propsData: {
                initialElements: DATA._2,
                creationFn: () => {
                    return;
                },
                oncreate: () => {
                    return;
                },
                oncancel: () => {
                    return;
                },
                hideSourceItems: false,
            },
        });
        await wrapper.vm.$nextTick();
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
        await wrapper.find("a.autopair-link").trigger("click");
        //assert pair-name longer name
        const pairname = wrapper.find("span.pair-name");
        expect(pairname.text()).toBe("DP134_1_FS_PSII_FSB_42C_A10");
    });

    it("removes the period from autopair name", async () => {
        wrapper = mount(PairedListCollectionCreator, {
            propsData: {
                initialElements: DATA._3,
                creationFn: () => {
                    return;
                },
                oncreate: () => {
                    return;
                },
                oncancel: () => {
                    return;
                },
                hideSourceItems: false,
            },
        });
        await wrapper.vm.$nextTick();
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
        await wrapper.find("a.autopair-link").trigger("click");
        //assert pair-name longer name
        const pairname = wrapper.find("span.pair-name");
        expect(pairname.text()).toBe("UII_moo_1");
    });

    it("autopairs correctly when filters are typed in", async () => {
        wrapper = mount(PairedListCollectionCreator, {
            propsData: {
                initialElements: DATA._4,
                creationFn: () => {
                    return;
                },
                oncreate: () => {
                    return;
                },
                oncancel: () => {
                    return;
                },
                hideSourceItems: false,
            },
        });
        await wrapper.vm.$nextTick();
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
        await wrapper.find("a.autopair-link").trigger("click");
        //assert all pairs matched
        expect(wrapper.findAll("li.dataset unpaired").length == 0).toBeTruthy();
    });
});
