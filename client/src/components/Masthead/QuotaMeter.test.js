import Vuex from "vuex";
import QuotaMeter from "./QuotaMeter.vue";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { userStore } from "store/userStore";
import { configStore } from "store/configStore";

const localVue = getLocalVue();

const createStore = (currentUser, config) => {
    return new Vuex.Store({
        modules: {
            config: {
                state: {
                    config,
                },
                getters: configStore.getters,
                namespaced: true,
            },
            user: {
                state: {
                    currentUser,
                },
                actions: {
                    loadUser: jest.fn(),
                },
                getters: userStore.getters,
                namespaced: true,
            },
        },
    });
};

describe("QuotaMeter.vue", () => {
    it("shows a percentage usage", () => {
        const user = {
            total_disk_usage: 5120,
            quota_percent: 50,
        };

        const config = { enable_quotas: true };
        const store = createStore(user, config);
        const wrapper = mount(QuotaMeter, { localVue, store });

        expect(wrapper.find(".quota-progress > span").text()).toBe("Using 50%");
    });

    it("changes appearance depending on usage", () => {
        const config = { enable_quotas: true };

        {
            const user = { quota_percent: 30 };
            const store = createStore(user, config);
            const wrapper = mount(QuotaMeter, { localVue, store });

            expect(wrapper.find(".quota-progress .progress-bar").classes()).toContain("bg-success");
        }

        {
            const user = { quota_percent: 80 };
            const store = createStore(user, config);
            const wrapper = mount(QuotaMeter, { localVue, store });

            expect(wrapper.find(".quota-progress .progress-bar").classes()).toContain("bg-warning");
        }

        {
            const user = { quota_percent: 95 };
            const store = createStore(user, config);
            const wrapper = mount(QuotaMeter, { localVue, store });

            expect(wrapper.find(".quota-progress .progress-bar").classes()).toContain("bg-danger");
        }
    });

    it("prompts user to log in", () => {
        const config = { enable_quotas: true };
        const store = createStore({}, config);
        const wrapper = mount(QuotaMeter, { localVue, store });

        expect(wrapper.find(".quota-meter > a").attributes("title")).toContain("Log in");
    });

    it("shows total usage in title", () => {
        const user = { total_disk_usage: 9216 };
        const config = { enable_quotas: true };
        const store = createStore(user, config);
        const wrapper = mount(QuotaMeter, { localVue, store });

        expect(wrapper.find(".quota-progress").attributes("title")).toContain("9 KB");
    });

    it("shows total usage when there is no quota", () => {
        {
            const user = { total_disk_usage: 7168 };
            const config = { enable_quotas: false };
            const store = createStore(user, config);
            const wrapper = mount(QuotaMeter, { localVue, store });

            expect(wrapper.find(".quota-meter > a").text()).toBe("Using 7 KB");
            expect(wrapper.find(".quota-meter > a").attributes("title")).not.toContain("7 KB");
        }

        {
            const user = {
                total_disk_usage: 21504,
                quota: "unlimited",
            };

            const config = { enable_quotas: true };
            const store = createStore(user, config);
            const wrapper = mount(QuotaMeter, { localVue, store });

            expect(wrapper.find(".quota-meter > a").text()).toBe("Using 21 KB");
            expect(wrapper.find(".quota-meter > a").attributes("title")).not.toContain("21 KB");
        }
    });
});
