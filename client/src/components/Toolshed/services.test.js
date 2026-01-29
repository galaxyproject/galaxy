import { Services } from "./services";

describe("Toolshed service helpers", () => {
    const incoming = [
        {
            name: "name_0",
            owner: "owner_0",
            status: "status_0_0",
            description: "description_0_0",
            tool_shed: "url_1",
            ctx_rev: "1",
        },
        {
            name: "name_0",
            owner: "owner_0",
            status: "status_0_1",
            description: "description_0_1",
            tool_shed: "url_1",
            ctx_rev: "3",
        },
        {
            name: "name_1",
            owner: "owner_1",
            status: "status_1",
            description: "description_1",
            tool_shed: "url_2",
            ctx_rev: "42",
        },
        {
            name: "name_2",
            owner: "owner_2",
            status: "Installed",
            description: "description_2",
            tool_shed: "url_2",
            ctx_rev: "1",
        },
    ];
    const urls = ["http://url_1.com", "http://url_2.com"];

    it("test fix toolshed helper", () => {
        const services = new Services();
        const filter = (x) => x.status !== "Installed";
        const grouped = services._groupByNameOwnerToolshed(incoming, filter, true);
        services._fixToolshedUrls(grouped, urls);
        expect(grouped.length).toBe(2);
        expect(grouped[0].name).toBe("name_0");
        expect(grouped[0].tool_shed_url).toBe("http://url_1.com");
        expect(grouped[0].ctx_rev).toBe("3");
        expect(grouped[1].name === "name_1");
        expect(grouped[1].tool_shed_url).toBe("http://url_2.com");
    });
});
