import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { setMockConfig } from "@/composables/__mocks__/config";
import { useExportForAnotherGalaxy } from "@/composables/exportForAnotherGalaxy";
import { useHistoryStore } from "@/stores/historyStore";

import AnotherGalaxyPicker from "./AnotherGalaxyPicker.vue";

vi.mock("@/composables/config");

const PREPARE = "/api/histories/{history_id}/contents/{type}s/{id}/prepare_store_download";
const NONCE = "0123456789abcdef0123456789abcdef";
const TARGET = "https://usegalaxy.eu";

const { server, http } = useServerMock();

function row(id: string, overrides: Record<string, unknown> = {}) {
    return {
        id,
        name: `reads ${id}`,
        history_id: "h1",
        history_content_type: "dataset",
        hid: 1,
        state: "ok",
        visible: true,
        deleted: false,
        purged: false,
        ...overrides,
    };
}

let opener: { postMessage: ReturnType<typeof vi.fn> } | null;
let closeSpy: ReturnType<typeof vi.spyOn>;
let mounted: VueWrapper[] = [];
let datasetQueries: URLSearchParams[] = [];

function serveItems(items: Record<string, unknown>[], failing: string[] = []) {
    server.use(
        http.get("/api/datasets", ({ request, response }) => {
            datasetQueries.push(new URL(request.url).searchParams);
            return response(200).json(items as never, { headers: { total_matches: String(items.length) } });
        }),
        http.get("/api/histories/{history_id}", ({ response }) =>
            response(200).json({ id: "h1", name: "RNA" } as never),
        ),
        http.post(PREPARE, ({ params, response }) =>
            response(200).json({ storage_request_id: `req-${params.id}`, task: { id: `task-${params.id}` } } as never),
        ),
        http.get("/api/tasks/{task_id}/state", ({ params, response }) =>
            response(200).json((failing.includes(String(params.task_id)) ? "FAILURE" : "SUCCESS") as never),
        ),
        http.get("/api/tasks/{task_id}/result", ({ response }) =>
            response(200).json({ state: "FAILURE", result: "the file is missing" } as never),
        ),
    );
}

async function mountPicker(query: { returnTo?: unknown; nonce?: unknown } = { returnTo: TARGET, nonce: NONCE }) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    useHistoryStore().setHistories([
        { id: "h1", name: "RNA" },
        { id: "h2", name: "Old", deleted: true },
        { id: "h3", name: "Kept", archived: true },
    ] as never);
    const wrapper = mount(AnotherGalaxyPicker as object, { props: query, global: withPlugins(getLocalVue(), pinia) });
    mounted.push(wrapper);
    await flushPromises();
    return wrapper;
}

function messages() {
    return opener?.postMessage.mock.calls ?? [];
}

async function tick(wrapper: VueWrapper, key: string) {
    await wrapper.find(`[data-description="picker select ${key}"]`).setValue(true);
}

beforeEach(() => {
    datasetQueries = [];
    opener = { postMessage: vi.fn() };
    vi.spyOn(window, "opener", "get").mockImplementation(() => opener);
    closeSpy = vi.spyOn(window, "close").mockImplementation(() => {});
    setMockConfig({ enable_celery_tasks: true, version_major: "27.0" });
});

afterEach(() => {
    useExportForAnotherGalaxy().stopAll();
    mounted.forEach((wrapper) => wrapper.unmount());
    mounted = [];
    vi.restoreAllMocks();
});

describe("AnotherGalaxyPicker", () => {
    it("says hello to the exact return origin with this Galaxy's root and the nonce", async () => {
        serveItems([]);
        await mountPicker();
        expect(messages()).toEqual([
            [
                {
                    type: "galaxy-picker/hello",
                    protocol: 1,
                    version: "27.0",
                    root: `${window.location.origin}/`,
                    nonce: NONCE,
                },
                TARGET,
            ],
        ]);
    });

    it.each([
        ["a page address", { returnTo: `${TARGET}/datasets/list`, nonce: NONCE }],
        ["plain http", { returnTo: "http://usegalaxy.eu", nonce: NONCE }],
        ["no return address", { nonce: NONCE }],
        ["no nonce", { returnTo: TARGET }],
        ["a nonce with other characters", { returnTo: TARGET, nonce: "<script>" }],
    ])("refuses %s and offers nothing to send", async (_, query) => {
        serveItems([row("d1")]);
        const wrapper = await mountPicker(query);
        expect(wrapper.find('[data-description="picker invalid request"]').exists()).toBe(true);
        expect(wrapper.find('[data-description="picker send"]').exists()).toBe(false);
        expect(datasetQueries).toHaveLength(0);
        expect(messages()).toEqual([]);
    });

    it("lists visible, undeleted items of all histories and only lets finished ones be ticked", async () => {
        serveItems([
            row("d1"),
            row("d2", { state: "running" }),
            row("c1", {
                history_content_type: "dataset_collection",
                populated_state: "ok",
                elements_states: { ok: 2 },
            }),
        ]);
        const wrapper = await mountPicker();
        expect(datasetQueries[0]!.getAll("q")).toEqual(["deleted", "visible"]);
        expect(datasetQueries[0]!.getAll("qv")).toEqual(["false", "true"]);
        expect(datasetQueries[0]!.has("history_id")).toBe(false);
        expect(wrapper.find('[data-description="picker select dataset:d1"]').attributes("disabled")).toBeUndefined();
        expect(wrapper.find('[data-description="picker select dataset:d2"]').attributes("disabled")).toBeDefined();
        expect(
            wrapper.find('[data-description="picker select dataset_collection:c1"]').attributes("disabled"),
        ).toBeUndefined();
    });

    it.each([
        ["a deleted history", "h2", "In a deleted history"],
        ["an archived history", "h3", "In an archived history"],
    ])("lists items in %s but does not let them be ticked", async (_, historyId, reason) => {
        serveItems([row("d1", { history_id: historyId })]);
        const wrapper = await mountPicker();
        const checkbox = wrapper.find('[data-description="picker select dataset:d1"]');
        expect(checkbox.attributes("disabled")).toBeDefined();
        expect(checkbox.element.closest("label")?.getAttribute("title")).toBe(reason);
        await tick(wrapper, "dataset:d1");
        expect(wrapper.find('[data-description="picker send"]').attributes("aria-disabled")).toBe("true");
    });

    it("names the target and the number of items before anything is sent", async () => {
        serveItems([row("d1"), row("d2")]);
        const wrapper = await mountPicker();
        const send = wrapper.find('[data-description="picker send"]');
        expect(send.text()).toBe("Send to usegalaxy.eu");
        expect(send.attributes("aria-disabled")).toBe("true");
        await tick(wrapper, "dataset:d1");
        await tick(wrapper, "dataset:d2");
        const consent = wrapper.find('[data-description="picker consent"]').text();
        expect(consent).toContain("Send 2 items to usegalaxy.eu");
        expect(consent).toContain("Anyone with these links can download the items");
        await flushPromises();
        expect(messages().map(([message]) => (message as { type: string }).type)).toEqual(["galaxy-picker/hello"]);
    });

    it.each([
        [{ short_term_storage_effective_duration: 172800 }, "usually after 2 days"],
        [{ short_term_storage_effective_duration: undefined }, "usually after 24 hours"],
    ])("states this Galaxy's link lifetime in the consent text for %j", async (config, text) => {
        setMockConfig({ enable_celery_tasks: true, version_major: "27.0", ...config });
        serveItems([row("d1")]);
        const withOpener = await mountPicker();
        expect(withOpener.find('[data-description="picker consent"]').text()).toContain(text);
        opener = null;
        const withoutOpener = await mountPicker();
        expect(withoutOpener.find('[data-description="picker consent"]').text()).toContain(text);
    });

    it("renders and posts with a real cross-origin opener, whose other properties throw on read", async () => {
        const postMessage = vi.fn();
        const crossOrigin = new Proxy(
            {},
            {
                get(_target, property) {
                    if (property === "postMessage") {
                        return postMessage;
                    }
                    throw new DOMException(`Blocked reading ${String(property)}`, "SecurityError");
                },
            },
        );
        vi.spyOn(window, "opener", "get").mockImplementation(() => crossOrigin);
        serveItems([row("d1")]);
        const wrapper = await mountPicker();
        expect(wrapper.find('[data-description="picker send"]').text()).toBe("Send to usegalaxy.eu");
        expect(wrapper.find('[data-description="picker no opener"]').exists()).toBe(false);
        expect(postMessage).toHaveBeenCalledWith(expect.objectContaining({ type: "galaxy-picker/hello" }), TARGET);
    });

    it("sends the links to the exact return origin once every export is ready, then closes", async () => {
        serveItems([
            row("d1"),
            row("c1", {
                history_content_type: "dataset_collection",
                name: "pairs",
                populated_state: "ok",
                elements_states: { ok: 2 },
            }),
        ]);
        const wrapper = await mountPicker();
        await tick(wrapper, "dataset:d1");
        await tick(wrapper, "dataset_collection:c1");
        await wrapper.find('[data-description="picker send"]').trigger("click");
        await vi.waitFor(() => expect(closeSpy).toHaveBeenCalled(), { timeout: 5000 });
        const [result, origin] = messages().at(-1)!;
        expect(origin).toBe(TARGET);
        expect(result).toEqual({
            type: "galaxy-picker/result",
            protocol: 1,
            nonce: NONCE,
            items: [
                { type: "dataset", name: "reads d1", link: `${window.location.origin}/api/short_term_storage/req-d1` },
                {
                    type: "dataset_collection",
                    name: "pairs",
                    link: `${window.location.origin}/api/short_term_storage/req-c1`,
                },
            ],
            failed: 0,
        });
    });

    it("still sends the items that exported, lists the ones that failed and stays open", async () => {
        serveItems([row("d1"), row("d2")], ["task-d2"]);
        const wrapper = await mountPicker();
        await tick(wrapper, "dataset:d1");
        await tick(wrapper, "dataset:d2");
        await wrapper.find('[data-description="picker send"]').trigger("click");
        await vi.waitFor(() => expect(wrapper.find('[data-description="picker sent"]').exists()).toBe(true), {
            timeout: 5000,
        });
        const [result] = messages().at(-1)!;
        expect(result.items.map((item: { name: string }) => item.name)).toEqual(["reads d1"]);
        expect(result.failed).toBe(1);
        expect(wrapper.text()).toContain("Could not be exported: the file is missing");
        expect(closeSpy).not.toHaveBeenCalled();
    });

    it("reports the failures to the target when no item exported, so Close does not read as a cancel", async () => {
        serveItems([row("d1"), row("d2")], ["task-d1", "task-d2"]);
        const wrapper = await mountPicker();
        await tick(wrapper, "dataset:d1");
        await tick(wrapper, "dataset:d2");
        await wrapper.find('[data-description="picker send"]').trigger("click");
        await vi.waitFor(() => expect(wrapper.find('[data-description="picker none sent"]').exists()).toBe(true), {
            timeout: 5000,
        });
        const expected = [{ type: "galaxy-picker/result", protocol: 1, nonce: NONCE, items: [], failed: 2 }, TARGET];
        expect(messages().at(-1)).toEqual(expected);
        expect(closeSpy).not.toHaveBeenCalled();
        await wrapper.find('[data-description="picker close"]').trigger("click");
        expect(messages().at(-1)).toEqual(expected);
        expect(closeSpy).toHaveBeenCalled();
    });

    it("shows the links to copy when no window opened it", async () => {
        opener = null;
        serveItems([row("d1")]);
        const wrapper = await mountPicker();
        expect(wrapper.find('[data-description="picker no opener"]').exists()).toBe(true);
        await tick(wrapper, "dataset:d1");
        const send = wrapper.find('[data-description="picker send"]');
        expect(send.text()).toBe("Make links");
        await send.trigger("click");
        await vi.waitFor(() => expect(wrapper.find('[data-description="picker link"]').exists()).toBe(true), {
            timeout: 5000,
        });
        const link = wrapper.find('[data-description="picker link"]').element as HTMLInputElement;
        expect(link.value).toBe(`${window.location.origin}/api/short_term_storage/req-d1`);
        expect(closeSpy).not.toHaveBeenCalled();
    });

    it("tells the target when nothing is chosen", async () => {
        serveItems([row("d1")]);
        const wrapper = await mountPicker();
        await wrapper.find('[data-description="picker cancel"]').trigger("click");
        expect(messages().at(-1)).toEqual([{ type: "galaxy-picker/cancel", nonce: NONCE }, TARGET]);
        expect(closeSpy).toHaveBeenCalled();
    });

    it("shows the results of the latest search when an earlier one comes back last", async () => {
        serveItems([]);
        let releaseFirst: () => void = () => {};
        const firstHeld = new Promise<void>((resolve) => (releaseFirst = resolve));
        server.use(
            http.get("/api/datasets", async ({ request, response }) => {
                const term = new URL(request.url).searchParams.getAll("qv")[2];
                datasetQueries.push(new URL(request.url).searchParams);
                if (!term) {
                    await firstHeld;
                }
                const items = [row(term ? "new" : "old")];
                return response(200).json(items as never, { headers: { total_matches: "1" } });
            }),
        );
        const wrapper = await mountPicker();
        await wrapper.find('[data-description="picker search"]').setValue("reads");
        await vi.waitFor(() =>
            expect(wrapper.find('[data-description="picker select dataset:new"]').exists()).toBe(true),
        );
        releaseFirst();
        await vi.waitFor(() => expect(datasetQueries).toHaveLength(2));
        await flushPromises();
        expect(wrapper.find('[data-description="picker select dataset:old"]').exists()).toBe(false);
        expect(wrapper.find('[data-description="picker select dataset:new"]').exists()).toBe(true);
    });

    it("says so when this Galaxy cannot export", async () => {
        setMockConfig({ enable_celery_tasks: false });
        serveItems([row("d1")]);
        const wrapper = await mountPicker();
        expect(wrapper.find('[data-description="picker cannot export"]').exists()).toBe(true);
        expect(wrapper.find('[data-description="picker send"]').exists()).toBe(false);
    });
});
