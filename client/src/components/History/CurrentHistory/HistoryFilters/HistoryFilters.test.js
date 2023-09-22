import { mount } from "@vue/test-utils";
import HistoryFilters from "./HistoryFilters";
import { getLocalVue } from "tests/jest/helpers";
import { HistoryFilters as HistoryFiltering } from "components/History/HistoryFilters";

const localVue = getLocalVue();

describe("HistoryFilters", () => {
    let wrapper;

    async function expectCorrectEmits(showAdvanced, filterText) {
        // count how many times filterText and toggles are emitted
        const filterEmit = wrapper.emitted()["update:filter-text"].length - 1;
        const toggleEmit = wrapper.emitted()["update:show-advanced"].length - 1;
        expect(wrapper.emitted()["update:show-advanced"][toggleEmit][0]).toEqual(showAdvanced);
        await wrapper.setProps({ showAdvanced: wrapper.emitted()["update:show-advanced"][toggleEmit][0] });
        const receivedText = wrapper.emitted()["update:filter-text"][filterEmit][0];
        const receivedDict = HistoryFiltering.getQueryDict(receivedText);
        const parsedDict = HistoryFiltering.getQueryDict(filterText);
        expect(receivedDict).toEqual(parsedDict);
    }

    beforeEach(() => {
        wrapper = mount(HistoryFilters, {
            propsData: {
                filterText: "",
                showAdvanced: false,
            },
            localVue,
            stubs: {
                icon: { template: "<div></div>" },
            },
        });
    });

    it("test history items filter panel", async () => {
        expect(wrapper.find("[description='advanced filters']").exists()).toBe(false);
        await wrapper.setProps({ showAdvanced: true });
        expect(wrapper.find("[description='advanced filters']").exists()).toBe(true);
        expect(wrapper.find("[description='advanced filters']").exists()).toBe(true);
        const filterInputs = {
            "[placeholder='any name']": "name-filter",
            "[placeholder='any extension']": "ext-filter",
            "[placeholder='any tag']": "tag filter",
            "[placeholder='any state']": "state-filter",
            "[placeholder='any database']": "db-filter",
            "[placeholder='index equals']": "hid-related",
            "[placeholder='index greater']": "hid-greater",
            "[placeholder='index lower']": "hid-lower",
            "[placeholder='created after']": "January 1, 2022",
            "[placeholder='created before']": "January 1, 2023",
        };

        // only add name filter in the advanced menu
        let filterName = wrapper.find("[placeholder='any name']");
        if (filterName.vm && filterName.props().type == "text") {
            filterName.setValue(filterInputs["[placeholder='any name']"]);
        }

        // Test: keyup.enter search (should toggle the view out)
        await filterName.trigger("keyup.enter");
        await expectCorrectEmits(false, "name:name-filter");

        // Test: clearing the filterText
        const clearButton = wrapper.find("[data-description='clear filters']");
        await clearButton.trigger("click");
        await expectCorrectEmits(false, "");

        // Test: toggling view back in
        const toggleButton = wrapper.find("[data-description='show advanced filter toggle']");
        await toggleButton.trigger("click");
        await expectCorrectEmits(true, "");

        // Now add filters in all input fields in the advanced menu
        Object.entries(filterInputs).forEach(([selector, value]) => {
            const filterInput = wrapper.find(selector);
            if (filterInput.vm && filterInput.props().type == "text") {
                filterInput.setValue(value);
            }
        });

        // Test: search button (should toggle the view out)
        const searchButton = wrapper.find("[description='apply filters']");
        await searchButton.trigger("click");

        await expectCorrectEmits(
            false,
            "create_time>'January 1, 2022' create_time<'January 1, 2023' extension:ext-filter genome_build:db-filter related:hid-related hid>hid-greater hid<hid-lower name:name-filter state:state-filter tag:'tag filter'"
        );

        // -------- Test esc key:  ---------
        // toggles view out only (doesn't cause a new search / doesn't emulate enter)

        // clear the filterText
        await clearButton.trigger("click");

        // toggle view back in
        await toggleButton.trigger("click");
        await expectCorrectEmits(true, "");

        // find name field again (could be destroyed beacause of toggling out)
        filterName = wrapper.find("[placeholder='any name']");
        if (filterName.vm && filterName.props().type == "text") {
            filterName.setValue("newnamefilter");
        }

        // press esc key from name field (should not change emitted filterText unlike enter key)
        await filterName.trigger("keyup.esc");
        await expectCorrectEmits(false, "");
    });

    it("test radio-group default filters", async () => {
        // -------- Testing deleted filter first:  ---------

        await wrapper.setProps({ showAdvanced: true });
        const deletedFilterBtnGrp = wrapper.find("[description='filter deleted']");
        const deletedFilterAnyBtn = deletedFilterBtnGrp.find(".btn-secondary");
        expect(deletedFilterAnyBtn.text()).toBe("Any");

        // current active button for deleted filter should be "No"
        let deletedFilterActiveBtn = deletedFilterBtnGrp.find(".btn-secondary.active");
        expect(deletedFilterActiveBtn.text()).toBe("No");

        await deletedFilterAnyBtn.find("input").setChecked();

        // now active button for deleted filter should be "Any"
        deletedFilterActiveBtn = deletedFilterBtnGrp.find(".btn-secondary.active");
        expect(deletedFilterActiveBtn.text()).toBe("Any");

        // expect "deleted = any" filter to be applied
        let searchButton = wrapper.find("[description='apply filters']");
        await searchButton.trigger("click");
        await expectCorrectEmits(false, "visible:true");

        // -------- Testing visible filter now:  ---------

        const toggleButton = wrapper.find("[data-description='show advanced filter toggle']");
        await toggleButton.trigger("click");
        await expectCorrectEmits(true, "visible:true");
        const visibleFilterBtnGrp = wrapper.find("[description='filter visible']");
        const visibleFilterAnyBtn = visibleFilterBtnGrp.find(".btn-secondary");
        expect(visibleFilterAnyBtn.text()).toBe("Any");

        // current active button for visible filter should be "Yes"
        let visibleFilterActiveBtn = visibleFilterBtnGrp.find(".btn-secondary.active");
        expect(visibleFilterActiveBtn.text()).toBe("Yes");

        await visibleFilterAnyBtn.find("input").setChecked();

        // now active button for visible filter should be "Any"
        visibleFilterActiveBtn = visibleFilterBtnGrp.find(".btn-secondary.active");
        expect(visibleFilterActiveBtn.text()).toBe("Any");

        // expect "visible = any" filter to be applied
        searchButton = wrapper.find("[description='apply filters']");
        await searchButton.trigger("click");
        await expectCorrectEmits(false, "deleted:any visible:any");

        // -------- Testing repeated search if it prevents bug:  ---------
        // (bug reported here: https://github.com/galaxyproject/galaxy/issues/16211)
        await toggleButton.trigger("click");
        await expectCorrectEmits(true, "deleted:any visible:any");
        searchButton = wrapper.find("[description='apply filters']");
        await searchButton.trigger("click");
        await expectCorrectEmits(false, "deleted:any visible:any");
    });
});
