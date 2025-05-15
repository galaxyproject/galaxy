import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import DefaultBox from "./DefaultBox.vue";

const localVue = getLocalVue();

type IntersectionObserverType = {
    new (callback: IntersectionObserverCallback, options?: IntersectionObserverInit): IntersectionObserver;
    prototype: IntersectionObserver;
};

function getWrapper() {
    return mount(DefaultBox as object, {
        propsData: {
            chunkUploadSize: 100,
            defaultDbKey: "?",
            defaultExtension: "auto",
            effectiveExtensions: [{ id: "ab1" }],
            fileSourcesConfigured: true,
            ftpUploadSite: null,
            historyId: "historyId",
            lazyLoad: 3,
            listDbKeys: [],
        },
        localVue,
        stubs: {
            FontAwesomeIcon: true,
        },
        pinia: createTestingPinia(),
    });
}

describe("Default", () => {
    let UnpatchedIntersectionObserver: IntersectionObserverType;

    beforeEach(() => {
        UnpatchedIntersectionObserver = global.IntersectionObserver;

        // The use of b-textarea in this DefaultRow causes the following warning:
        // [Vue warn]: Error in directive b-visible unbind hook: "TypeError: this.observer.disconnect is not a function"
        // I don't think there is a problem with the usage so I think this a bug in bootstrap vue, it can be worked around
        // with the following code - but just suppressing the warning is probably better?
        const observerMock = jest.fn(function IntersectionObserver(callback: IntersectionObserverCallback) {
            this.observe = jest.fn();
            this.disconnect = jest.fn();
            this.trigger = (mockedMutationsList: IntersectionObserverEntry[]) => {
                callback(mockedMutationsList, this);
            };
        });
        global.IntersectionObserver = observerMock as unknown as IntersectionObserverType;
    });

    afterEach(() => {
        global.IntersectionObserver = UnpatchedIntersectionObserver;
    });

    it("rendering", async () => {
        const wrapper = getWrapper();
        expect((wrapper.vm as any).counterAnnounce).toBe(0);
        expect((wrapper.vm as any).showHelper).toBe(true);
        expect((wrapper.vm as any).listExtensions[0].id).toBe("ab1");
        expect(wrapper.find("#btn-reset").classes()).toEqual(expect.arrayContaining(["disabled"]));
        expect(wrapper.find("#btn-start").classes()).toEqual(expect.arrayContaining(["disabled"]));
        expect(wrapper.find("#btn-stop").classes()).toEqual(expect.arrayContaining(["disabled"]));
        await flushPromises();
    });

    it("resets properly", async () => {
        const wrapper = getWrapper();
        expect((wrapper.vm as any).showHelper).toBe(true);
        await wrapper.find("#btn-new").trigger("click");
        expect((wrapper.vm as any).showHelper).toBe(false);
        expect((wrapper.vm as any).counterAnnounce).toBe(1);
        await wrapper.find("#btn-reset").trigger("click");
        expect((wrapper.vm as any).showHelper).toBe(true);
        await flushPromises();
    });

    it("does render remote files button", async () => {
        const wrapper = getWrapper();
        expect(wrapper.find("#btn-remote-files").exists()).toBeTruthy();
        await wrapper.setProps({ fileSourcesConfigured: false });
        expect(wrapper.find("#btn-remote-files").exists()).toBeFalsy();
        await flushPromises();
    });

    it("renders a limited set", async () => {
        const wrapper = getWrapper();
        for (let i = 0; i < 5; i++) {
            await wrapper.find("#btn-new").trigger("click");
        }
        expect(wrapper.findAll(".upload-row").length).toBe(3);
        const textMessage = wrapper.find("[data-description='lazyload message']");
        expect(textMessage.text()).toBe("Only showing first 3 of 5 entries.");
        await flushPromises();
    });
});
