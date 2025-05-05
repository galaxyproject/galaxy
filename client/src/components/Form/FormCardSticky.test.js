import { faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { mount } from "@vue/test-utils";

import FormCardSticky from "./FormCardSticky.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

describe("FormCardSticky.vue", () => {
    const defaultProps = {
        name: "Tool Name",
        description: "This is a test tool",
        version: "23.0",
        icon: faWrench,
        logo: "/static/logo.svg",
        errorMessage: "",
        isLoading: false,
    };

    const mountComponent = (props = {}, slots = {}) => {
        return mount(FormCardSticky, {
            propsData: { ...defaultProps, ...props },
            global: {
                components: {
                    Heading,
                    LoadingSpan,
                },
            },
            slots,
        });
    };

    it("renders error alert when errorMessage is present", () => {
        const wrapper = mountComponent({ errorMessage: "Something went wrong" });
        expect(wrapper.findComponent({ name: "BAlert" }).exists()).toBe(true);
        expect(wrapper.text()).toContain("Something went wrong");
    });

    it("renders loading state when isLoading is true", () => {
        const wrapper = mountComponent({ isLoading: true, errorMessage: "" });
        expect(wrapper.findComponent(LoadingSpan).exists()).toBe(true);
    });

    it("renders logo when provided", () => {
        const wrapper = mountComponent();
        const logoImg = wrapper.find("img[alt='logo']");
        expect(logoImg.exists()).toBe(true);
        expect(logoImg.attributes("src")).toBe("http://localhost/static/logo.svg");
    });

    it("renders icon fallback when logo is not provided", () => {
        const wrapper = mountComponent({ logo: undefined });
        const iconComponent = wrapper.findComponent(FontAwesomeIcon);
        expect(iconComponent.exists()).toBe(true);
        expect(iconComponent.classes()).toContain("fa-fw");
        const logoImg = wrapper.find("img[alt='logo']");
        expect(logoImg.exists()).toBe(false);
    });

    it("renders name, description, and version", () => {
        const wrapper = mountComponent();
        expect(wrapper.find("h1").text()).toBe("Tool Name");
        expect(wrapper.text()).toContain("This is a test tool");
        expect(wrapper.text()).toContain("(Galaxy Version 23.0)");
    });

    it("renders slot content: buttons, default, footer", () => {
        const wrapper = mountComponent(
            {},
            {
                buttons: "<button>Click me</button>",
                default: "<p>Main content</p>",
                footer: "<footer>Footer content</footer>",
            }
        );
        expect(wrapper.find("button").text()).toBe("Click me");
        expect(wrapper.find("#tool-card-body").text()).toContain("Main content");
        expect(wrapper.find("footer").text()).toContain("Footer content");
    });
});
