import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import AvailableVisualizationCard from "./AvailableVisualizationCard.vue";
import VisualizationCard from "./VisualizationCard.vue";

vi.mock("./services");

const localVue = getLocalVue();

function installedCard(metadata: Record<string, unknown>) {
    return mount(VisualizationCard as object, {
        global: localVue,
        props: {
            visualization: {
                id: "nora",
                package: "@galaxyproject/nora",
                version: "1.0.0",
                enabled: true,
                installed: true,
                metadata,
            },
        },
    });
}

function availableCard(links: Record<string, unknown>) {
    return mount(AvailableVisualizationCard as object, {
        global: localVue,
        props: { packageData: { name: "@galaxyproject/nora", version: "1.0.0", description: "", links } },
    });
}

function hrefs(wrapper: ReturnType<typeof mount>) {
    return wrapper.findAll("a").map((link) => link.attributes("href"));
}

describe("visualization cards", () => {
    // these URLs come from package.json and the npm registry, and the page runs with admin rights
    it("only links package homepages over http(s)", () => {
        expect(hrefs(installedCard({ homepage: "javascript:alert(1)" }))).not.toContain("javascript:alert(1)");
        expect(hrefs(installedCard({ homepage: "https://example.org/nora" }))).toContain("https://example.org/nora");
    });

    it("only links registry homepage and repository URLs over http(s)", () => {
        const wrapper = availableCard({ homepage: "javascript:alert(1)", repository: "https://github.com/x/nora" });
        expect(hrefs(wrapper)).not.toContain("javascript:alert(1)");
        expect(hrefs(wrapper)).toContain("https://github.com/x/nora");
    });

    it("shows an object-form package.json author by name", () => {
        const wrapper = installedCard({ author: { name: "Galaxy Team", email: "team@example.org" } });
        const authorLine = wrapper.findAll("span").find((span) => span.text().startsWith("Author:"));
        expect(authorLine?.text()).toBe("Author: Galaxy Team");
    });
});
