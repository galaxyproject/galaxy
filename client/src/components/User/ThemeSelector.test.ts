import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import ThemeSelector from "./ThemeSelector.vue";

const currentTheme = ref("blue");
const settingTheme = ref(false);
const setCurrentTheme = vi.fn();

vi.mock("@/composables/config", () => ({
    useConfig: () => ({
        config: ref({ logo_src: "/logo.png", themes: { blue: {}, dark: {} } }),
        isConfigLoaded: ref(true),
    }),
}));

vi.mock("@/composables/user", () => ({
    useCurrentTheme: () => ({ currentTheme, setCurrentTheme, settingTheme }),
}));

const localVue = getLocalVue();

function mountSelector() {
    return mount(ThemeSelector as object, { global: localVue });
}

function radios(wrapper: ReturnType<typeof mountSelector>) {
    return wrapper.findAll<HTMLInputElement>("input[type=radio]");
}

describe("ThemeSelector", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        currentTheme.value = "blue";
        settingTheme.value = false;
    });

    it("lists the themes in a named radio group with the current theme checked", () => {
        const wrapper = mountSelector();
        expect(wrapper.find("[role=radiogroup]").attributes("aria-label")).toBe("Theme");
        expect(radios(wrapper).map((radio) => radio.attributes("value"))).toEqual(["blue", "dark"]);
        expect(radios(wrapper).map((radio) => radio.element.checked)).toEqual([true, false]);
    });

    it("applies the chosen theme", async () => {
        const wrapper = mountSelector();
        await radios(wrapper)[1]!.setValue(true);
        expect(setCurrentTheme).toHaveBeenCalledWith("dark");
    });

    it("disables the themes while one is being applied", async () => {
        const wrapper = mountSelector();
        settingTheme.value = true;
        await wrapper.vm.$nextTick();
        expect(radios(wrapper).every((radio) => radio.element.disabled)).toBe(true);
    });
});
