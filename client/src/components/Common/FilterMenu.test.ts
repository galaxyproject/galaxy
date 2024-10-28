import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";

import { HistoryFilters } from "@/components/History/HistoryFilters";
import { setupSelectableMock } from "@/components/ObjectStore/mockServices";
import { getWorkflowFilters } from "@/components/Workflow/List/workflowFilters";
import Filtering, { compare, contains, equals, toBool, toDate } from "@/utils/filtering";

import FilterMenu from "./FilterMenu.vue";

setupSelectableMock();

const localVue = getLocalVue();
const options = [
    { text: "Any", value: "any" },
    { text: "Yes", value: true },
    { text: "No", value: false },
];
const validTestFilters = {
    /** A basic name filter (with same placeholder as the key) */
    name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
    /** A filter with different key and placeholder */
    filter_key: { placeholder: "item", type: String, handler: contains("filter_key"), menuItem: true },
    /** A filter with help component */
    has_help: {
        placeholder: "value",
        type: String,
        handler: equals("has_help"),
        helpInfo: "Some test help info",
        menuItem: true,
    },
    /** A filter with datalist */
    list_item: {
        placeholder: "list item",
        type: Number,
        handler: equals("list_item"),
        datalist: ["option1", "option2"],
        menuItem: true,
    },
    /** A ranged date filter */
    create_time: {
        placeholder: "creation time",
        type: Date,
        handler: compare("create_time", "le", toDate),
        isRangeInput: true,
        menuItem: true,
    },
    /** A ranged number filter */
    number: { placeholder: "index", type: Number, handler: equals("number"), isRangeInput: true, menuItem: true },
    /** A boolean filter with default boolType */
    bool_def: {
        placeholder: "Filter by option (any/yes/no)",
        type: Boolean,
        handler: equals("bool_def", "bool_def", toBool),
        menuItem: true,
    },
    /** A boolean filter with is:filter boolType */
    bool_is: {
        placeholder: "Filter by option (yes/no)",
        type: Boolean,
        handler: equals("bool_is", "bool_is", toBool),
        menuItem: true,
        boolType: "is" as const,
    },
    /** A valid filter, just not included in menu */
    not_included: { handler: contains("not_included"), menuItem: false },
};

const TestFilters = new Filtering(validTestFilters, undefined);

describe("FilterMenu", () => {
    let wrapper: Wrapper<Vue>;

    function setUpWrapper(name: string, placeholder: string, filterClass: Filtering<unknown>) {
        wrapper = mount(FilterMenu as object, {
            propsData: {
                name: name,
                placeholder: placeholder,
                filterClass: filterClass,
                filterText: "",
                showAdvanced: false,
            },
            localVue,
            stubs: {
                icon: { template: "<div></div>" },
            },
            pinia: createTestingPinia(),
        });
    }

    async function performSearch() {
        // Test: search button (should toggle the view out)
        const searchButton = wrapper.find("[data-description='apply filters']");
        await searchButton.trigger("click");
    }

    async function expectCorrectEmits(filterText: string, filterClass: Filtering<unknown>, showAdvanced?: boolean) {
        if (showAdvanced !== undefined) {
            const toggleEmit = (wrapper.emitted()?.["update:show-advanced"]?.length ?? 0) - 1;
            expect(wrapper.emitted()["update:show-advanced"]?.[toggleEmit]?.[0]).toEqual(showAdvanced);
            await wrapper.setProps({ showAdvanced: wrapper.emitted()["update:show-advanced"]?.[toggleEmit]?.[0] });
        }
        const filterEmit = (wrapper.emitted()["update:filter-text"]?.length ?? 0) - 1;
        const receivedText = wrapper.emitted()["update:filter-text"]?.[filterEmit]?.[0];
        const receivedDict = filterClass.getQueryDict(receivedText);
        const parsedDict = filterClass.getQueryDict(filterText);
        expect(receivedDict).toEqual(parsedDict);
    }

    it("test generic test items filter panel search", async () => {
        setUpWrapper("Test Items", "search test items", TestFilters);
        const validFilters = wrapper.vm.$props.filterClass.validFilters;

        await wrapper.setProps({ showAdvanced: true });

        const expectedFilters = [
            {
                label: "Filter by name:",
                placeholder: "any name",
                value: "name-filter",
            },
            {
                label: "Filter by item:",
                placeholder: "any item",
                value: "item-filter",
            },
            {
                label: "Filter by value:",
                placeholder: "any value",
                value: "has-help-filter",
            },
            {
                label: "Filter by list item:",
                placeholder: "any list item",
                value: "1234",
            },
        ];

        expect(Object.keys(validFilters).length).toBe(13);
        // find all labels for the filters
        const labels = wrapper.findAll("small");
        expect(labels.length).toBe(8);
        // 8 labels, but 15 valid filters
        // more valid filters than labels because not all all `menuItem:true`

        /**
         * Now add filters in all input fields in the advanced menu
         * and check that the correct query is emitted
         * */

        // First 4 filters are normal, non ranged input fields
        expectedFilters.forEach((expectedFilter, i) => {
            const label = labels.at(i);
            expect(label.text()).toBe(expectedFilter.label);
            if (i < 4) {
                const filterInput = wrapper.find(`[placeholder='${expectedFilter.placeholder}']`);
                expect(filterInput.exists()).toBe(true);
                filterInput.setValue(expectedFilter.value);
            }
        });
        // `has_help` filter should have help modal button
        expect(wrapper.find("[title='Value Help']").classes().includes("btn")).toBe(true);
        // ranged time field (has 2 datepickers)
        const createdGtInput = wrapper.find("[placeholder='after creation time']");
        const createdLtInput = wrapper.find("[placeholder='before creation time']");
        createdGtInput.setValue("January 1, 2022");
        createdLtInput.setValue("January 1, 2023");
        expect(wrapper.findAll(".b-form-datepicker").length).toBe(2);
        // ranged number field (has different placeholder: greater instead of after...)
        const indexGtInput = wrapper.find("[placeholder='greater than index']");
        const indexLtInput = wrapper.find("[placeholder='lower than index']");
        indexGtInput.setValue("1234");
        indexLtInput.setValue("5678");
        // default bool filter
        const radioBtnGrp = wrapper.find("[data-description='filter bool_def']").findAll(".btn-secondary");
        expect(radioBtnGrp.length).toBe(options.length);
        for (let i = 0; i < options.length; i++) {
            expect(radioBtnGrp.at(i).text()).toBe(options[i]?.text);
            expect(radioBtnGrp.at(i).props().value).toBe(options[i]?.value);
            expect(radioBtnGrp.at(i).props().checked).toBe(null);
        }
        await radioBtnGrp.at(1).find("input").setChecked(); // click "Yes"
        // boolean filter
        const boolBtnGrp = wrapper.find("[data-description='filter bool_is']").findAll(".btn-secondary");
        expect(boolBtnGrp.length).toBe(2);
        expect(boolBtnGrp.at(0).text()).toBe("Yes");
        expect(boolBtnGrp.at(0).props().value).toBe(true);
        expect(boolBtnGrp.at(1).text()).toBe("No");
        expect(boolBtnGrp.at(1).props().value).toBe("any");
        await boolBtnGrp.at(1).find("input").setChecked(); // click "No"

        // perform search
        await performSearch();
        await expectCorrectEmits(
            "create_time>'January 1, 2022' create_time<'January 1, 2023' " +
                "filter_key:item-filter has_help:has-help-filter list_item:1234 " +
                "number>1234 number<5678 name:name-filter radio:true bool_def:true",
            TestFilters,
            false
        );
    });

    it("test buttons that navigate menu and keyup.enter/esc events", async () => {
        setUpWrapper("Test Items", "search test items", TestFilters);

        expect(wrapper.find("[data-description='advanced filters']").exists()).toBe(false);
        await wrapper.setProps({ showAdvanced: true });
        expect(wrapper.find("[data-description='advanced filters']").exists()).toBe(true);

        // only add name filter in the advanced menu
        let filterName = wrapper.find("[placeholder='any name']");
        if (filterName.vm && filterName.props().type == "text") {
            await filterName.setValue("sample name");
        }

        // -------- Test keyup.enter key:  ---------
        // toggles view out and performs a search
        await filterName.trigger("keyup.enter");
        await expectCorrectEmits("name:'sample name'", TestFilters, false);

        // Test: clearing the filterText
        const clearButton = wrapper.find("[data-description='reset query']");
        await clearButton.trigger("click");
        await expectCorrectEmits("", TestFilters, false);

        // Test: toggling view back in
        const toggleButton = wrapper.find("[data-description='toggle advanced search']");
        await toggleButton.trigger("click");
        await expectCorrectEmits("", TestFilters, true);

        // -------- Test keyup.esc key:  ---------
        // toggles view out only (doesn't cause a new search / doesn't emulate enter)

        // find name field again (destroyed because of toggling out) and set value
        filterName = wrapper.find("[placeholder='any name']");
        if (filterName.vm && filterName.props().type == "text") {
            filterName.setValue("newnamefilter");
        }

        // press esc key from name field (should not change emitted filterText unlike enter key)
        await filterName.trigger("keyup.esc");
        await expectCorrectEmits("", TestFilters, false);
    });

    /**
     * Testing the default values of the filters defined in the HistoryFilters: Filtering
     * class, ensuring the default values are reflected in the radio-group buttons
     */
    it("test radio-group default filters on HistoryFilters", async () => {
        setUpWrapper("History Items", "search datasets", HistoryFilters);
        // -------- Testing deleted filter first:  ---------

        await wrapper.setProps({ showAdvanced: true });
        const deletedFilterBtnGrp = wrapper.find("[data-description='filter deleted']");
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
        await performSearch();
        await expectCorrectEmits("visible:true", HistoryFilters, false);

        // -------- Testing visible filter now:  ---------

        const toggleButton = wrapper.find("[data-description='toggle advanced search']");
        await toggleButton.trigger("click");
        await expectCorrectEmits("visible:true", HistoryFilters, true);
        const visibleFilterBtnGrp = wrapper.find("[data-description='filter visible']");
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
        await performSearch();
        await expectCorrectEmits("deleted:any visible:any", HistoryFilters, false);

        // -------- Testing repeated search if it prevents bug:  ---------
        // (bug reported here: https://github.com/galaxyproject/galaxy/issues/16211)
        await toggleButton.trigger("click");
        await expectCorrectEmits("deleted:any visible:any", HistoryFilters, true);
        await performSearch();
        await expectCorrectEmits("deleted:any visible:any", HistoryFilters, false);
    });

    /**
     * Testing the default values of the filters defined in the HistoryFilters: Filtering
     * class, ensuring the default values are reflected in the radio-group buttons
     */
    it("test compact menu with checkbox filters on WorkflowFilters", async () => {
        const myWorkflowFilters = getWorkflowFilters("my");
        setUpWrapper("Workflows", "search workflows", myWorkflowFilters);
        // a compact `FilterMenu` only needs to be opened once (doesn't toggle out automatically)
        await wrapper.setProps({ showAdvanced: true, view: "compact" });

        // -------- Testing auto search on value change:  ---------
        const nameFilterInput = wrapper.find("#workflows-advanced-filter-name");
        await nameFilterInput.setValue("myworkflow");
        await expectCorrectEmits("name:myworkflow", myWorkflowFilters);

        // -------- Testing deleted filter first:  ---------
        const deletedFilterCheckbox = wrapper.find("[data-description='filter deleted'] input");
        await deletedFilterCheckbox.setChecked();
        await expectCorrectEmits("name:myworkflow is:deleted", myWorkflowFilters);
    });
});
