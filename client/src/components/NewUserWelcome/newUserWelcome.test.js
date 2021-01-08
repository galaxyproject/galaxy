import { shallowMount, mount } from '@vue/test-utils';
import newUserWelcome from "./newUserWelcome.vue";
import { getLocalVue } from "jest/helpers";
import Topics from "components/NewUserWelcome/components/Topics";
import Subtopics from "components/NewUserWelcome/components/Subtopics";
import Slides from "components/NewUserWelcome/components/Slides";
import testData from "./testData.json";


const localVue = getLocalVue();

describe( 'New user first view', () => {
    let wrapper;
    let propsData;

    beforeEach(async () => {
        propsData = {
            newUserDict: testData,
        };
        wrapper = mount(newUserWelcome, {
            propsData,
            localVue,
        });
    });

    it("Contains standard header", async () => {
        expect(wrapper.find('.main-header').text()).toContain('Welcome to Galaxy');
    });
    it("Starts on overall topics", async () => {
        wrapper.setData({position: []});
        expect(wrapper.vm.depth).toBe(0);
        expect(wrapper.vm.currentDiv).toBe(Topics);
        expect(wrapper.vm.currentNode.topics).toHaveLength(1);
    });
});

describe( 'New user first view', () => {
    let wrapper;
    let propsData;

    beforeEach(async () => {
        propsData = {
            newUserDict: testData,
        };
        wrapper = shallowMount(newUserWelcome, {
            propsData,
            localVue,
        });
    });

    it("Starts on overall topics", async () => {
        wrapper.setData({"position": [0]});
        expect(wrapper.vm.depth).toBe(1);
        expect(wrapper.vm.currentDiv).toBe(Subtopics);
        expect(wrapper.vm.currentNode.topics).toHaveLength(2);
        expect(wrapper.vm.currentNode.title).toBe("testTopic");
    });
});

describe( 'New user first view', () => {
    let wrapper;
    let propsData;

    beforeEach(async () => {
        propsData = {
            newUserDict: testData,
        };
        wrapper = shallowMount(newUserWelcome, {
            propsData,
            localVue,
        });
    });

    it("Starts on overall topics", async () => {
        wrapper.setData({position: [0,0]});
        expect(wrapper.vm.depth).toBe(2);
        expect(wrapper.vm.currentDiv).toBe(Slides);
        expect(wrapper.vm.currentNode.title).toBe("subtopicTitle");
        expect(wrapper.vm.currentNode.slides).toHaveLength(3);
    });
});



    
    