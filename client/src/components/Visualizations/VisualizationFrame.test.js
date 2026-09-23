import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

import VisualizationFrame from "./VisualizationFrame.vue";

const PLUGIN = {
    href: "/static/plugins/visualizations/example/static",
    entry_point: { attr: { src: "index.js", css: "index.css" } },
};

vi.mock("axios", () => ({ default: { get: vi.fn(async () => ({ data: PLUGIN })) } }));
vi.mock("@/onload/loadConfig", () => ({ getAppRoot: () => "/" }));

let mounted = [];

function mountFrame(props) {
    const wrapper = mount(VisualizationFrame, {
        propsData: { name: "example", config: {}, ...props },
        attachTo: document.body,
    });
    mounted.push(wrapper);
    return wrapper;
}

const incomingOf = (wrapper) =>
    JSON.parse(wrapper.find("iframe").element.contentDocument.getElementById("app").getAttribute("data-incoming"));

const postFrom = (wrapper, data) =>
    window.dispatchEvent(new MessageEvent("message", { data, source: wrapper.find("iframe").element.contentWindow }));

afterEach(() => {
    mounted.forEach((wrapper) => wrapper.destroy());
    mounted = [];
    vi.useRealTimers();
});

describe("what the frame hands the plugin", () => {
    it("names the saved visualization it was opened from, and nothing when there is none", async () => {
        const saved = mountFrame({ visualizationId: "abc123" });
        const unsaved = mountFrame({});
        await flushPromises();
        expect(incomingOf(saved).visualization_id).toBe("abc123");
        expect(incomingOf(unsaved).visualization_id).toBeUndefined();
    });

    it("keeps sending the config, plugin and root alongside it", async () => {
        const wrapper = mountFrame({ config: { dataset_id: "d1" }, visualizationId: "abc123" });
        await flushPromises();
        expect(incomingOf(wrapper)).toMatchObject({
            visualization_config: { dataset_id: "d1" },
            visualization_plugin: PLUGIN,
            root: "http://localhost/",
        });
    });
});

describe("several visualizations on one page", () => {
    async function twoFrames() {
        const first = mountFrame({ config: { dataset_id: "d1" } });
        const second = mountFrame({ config: { dataset_id: "d2" } });
        await flushPromises();
        vi.useFakeTimers();
        return { first, second };
    }

    const settle = () => vi.advanceTimersByTimeAsync(400);

    it("routes each update to the visualization that sent it", async () => {
        const { first, second } = await twoFrames();
        postFrom(first, { from: "galaxy-visualization", visualization_title: "one" });
        postFrom(second, { from: "galaxy-visualization", visualization_title: "two" });
        await settle();
        expect(first.emitted("change")).toHaveLength(1);
        expect(second.emitted("change")).toHaveLength(1);
        expect(first.emitted("change")[0][0].visualization_title).toBe("one");
        expect(second.emitted("change")[0][0].visualization_title).toBe("two");
    });

    it("ignores a message from a window that is not its frame", async () => {
        const { first, second } = await twoFrames();
        window.dispatchEvent(
            new MessageEvent("message", {
                data: { from: "galaxy-visualization", visualization_title: "impostor" },
                source: window,
            }),
        );
        await settle();
        expect(first.emitted("change")).toBeFalsy();
        expect(second.emitted("change")).toBeFalsy();
    });

    it("does not emit a debounced change after it has been removed", async () => {
        const { first } = await twoFrames();
        postFrom(first, { from: "galaxy-visualization", visualization_title: "in flight" });
        first.destroy();
        await settle();
        expect(first.emitted("change")).toBeFalsy();
    });

    it("takes its listener off the shared window when removed", async () => {
        const added = vi.spyOn(window, "addEventListener");
        const removed = vi.spyOn(window, "removeEventListener");
        mountFrame({}).destroy();
        const handler = added.mock.calls.find(([type]) => type === "message")?.[1];
        expect(handler).toBeDefined();
        expect(removed.mock.calls).toContainEqual(["message", handler]);
    });
});
