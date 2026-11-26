import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { copy } from "@/utils/clipboard";

import EmbedCode from "./EmbedCode.vue";

vi.mock("@/utils/clipboard", () => ({ copy: vi.fn() }));

function mountCode(props: Record<string, string>) {
    return mount(EmbedCode as object, {
        props: { title: "Galaxy Page", url: "https://galaxy/widgets/pages/a1", ...props },
    });
}

afterEach(() => {
    vi.useRealTimers();
    vi.mocked(copy).mockClear();
});

describe("EmbedCode", () => {
    it("shows an iframe for the url with the given attributes", () => {
        const wrapper = mountCode({ attributes: 'style="border: none;"' });
        expect((wrapper.find(".embed-code-input").element as HTMLInputElement).value).toBe(
            '<iframe title="Galaxy Page" style="border: none;" src="https://galaxy/widgets/pages/a1"></iframe>',
        );
    });

    it("labels the embed code field", () => {
        const wrapper = mountCode({});
        expect(wrapper.get("label").attributes("for")).toBe("embed-code");
        expect(wrapper.get("input#embed-code").classes()).toContain("embed-code-input");
    });

    it("separates title and url without attributes", () => {
        const wrapper = mountCode({});
        expect((wrapper.find(".embed-code-input").element as HTMLInputElement).value).toBe(
            '<iframe title="Galaxy Page" src="https://galaxy/widgets/pages/a1"></iframe>',
        );
    });

    it("copies the code and says so for two seconds", async () => {
        vi.useFakeTimers();
        const wrapper = mountCode({});
        await wrapper.find("button").trigger("click");
        expect(copy).toHaveBeenCalledWith(
            '<iframe title="Galaxy Page" src="https://galaxy/widgets/pages/a1"></iframe>',
        );
        expect(wrapper.find("button").text()).toBe("Copied!");
        await vi.advanceTimersByTimeAsync(2000);
        expect(wrapper.find("button").text()).toBe("Copy");
    });
});
