import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useUploadState } from "@/components/Panels/Upload/uploadState";
import { setMockConfig } from "@/composables/__mocks__/config";
import { useHistoryStore } from "@/stores/historyStore";
import { useUploadTaskMonitorStore } from "@/stores/uploadTaskMonitorStore";

import GalaxyLinkImport from "./GalaxyLinkImport.vue";

vi.mock("@/composables/config");

const IMPORT = "/api/histories/{history_id}/contents_from_store_async";
const ITEM = '[data-description="galaxy picker import item"]';

const { server, http } = useServerMock();

function importEndsIn(state: string, reason = "") {
    const bodies: Record<string, unknown>[] = [];
    server.use(
        http.post(IMPORT, async ({ request, response }) => {
            bodies.push(await request.json());
            return response(200).json({ id: "task1", ignored: false } as never);
        }),
        http.get("/api/tasks/{task_id}/state", ({ response }) => response(200).json(state as never)),
        http.get("/api/tasks/{task_id}/result", ({ response }) =>
            response(200).json({ state, result: reason } as never),
        ),
    );
    return bodies;
}

let mountedLinks: VueWrapper[] = [];

async function enterLink(link: string, targetHistory?: { deleted?: boolean; archived?: boolean }) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    if (targetHistory) {
        useHistoryStore().setHistories([{ id: "hist_1", name: "Target", ...targetHistory } as never]);
    }
    const localVue = getLocalVue();
    const wrapper = mount(GalaxyLinkImport as object, {
        props: { method: { id: "galaxy-link" }, targetHistoryId: "hist_1" },
        global: { ...withPlugins(localVue, pinia), stubs: { ...localVue.stubs, SwitchToHistoryLink: true } },
    });
    mountedLinks.push(wrapper);
    await wrapper.find('[data-description="galaxy link import mode"] input[value="paste"]').setValue(true);
    await wrapper.find('[data-description="galaxy link input"]').setValue(link);
    return wrapper;
}

async function importLink(link: string) {
    const wrapper = await enterLink(link);
    await wrapper.find('[data-description="galaxy link import"]').trigger("click");
    return wrapper;
}

// Upload state is shared by every test, and imports left in it would keep being followed.
beforeEach(() => {
    useUploadState().clearAll();
});

afterEach(() => {
    // Each test has its own pinia, so its import monitor would otherwise follow the next test's imports too.
    useUploadTaskMonitorStore().$dispose();
    useUploadState().clearAll();
    vi.useRealTimers();
});

describe("GalaxyLinkImport, pasting a link", () => {
    afterEach(() => {
        mountedLinks.forEach((wrapper) => wrapper.unmount());
        mountedLinks = [];
    });

    it("imports the trimmed link in the background and says when it is done", async () => {
        const bodies = importEndsIn("SUCCESS");
        const wrapper = await importLink("  https://usegalaxy.org/api/short_term_storage/abc\n");
        await vi.waitFor(() => expect(wrapper.text()).toContain("Done!"));
        const input = wrapper.find('[data-description="galaxy link input"]');
        expect(input.classes()).toContain("g-form-input");
        expect((input.element as HTMLInputElement).value).toBe("");
        expect(wrapper.find('[data-description="galaxy link import"]').attributes("aria-disabled")).toBe("true");
        expect(bodies[0]).toEqual({
            store_content_uri: "https://usegalaxy.org/api/short_term_storage/abc",
            model_store_format: "tar.gz",
            discarded_data: "forbid",
        });
    });

    it("stops and explains when the import fails", async () => {
        importEndsIn("FAILURE", "404 Not Found");
        const wrapper = await importLink("https://usegalaxy.org/api/short_term_storage/old");
        await vi.waitFor(() => expect(wrapper.text()).toContain("may have expired"));
        expect(wrapper.text()).toContain("404 Not Found");
        expect(wrapper.find('[data-description="loading message"]').exists()).toBe(false);
    });

    it("does not call the import failed when Galaxy only could not report its progress", async () => {
        vi.useFakeTimers({ shouldAdvanceTime: true });
        importEndsIn("SUCCESS");
        let checks = 0;
        server.use(
            http.get("/api/tasks/{task_id}/state", ({ response }) => {
                checks++;
                return response("5XX").json({ err_msg: "Bad Gateway", err_code: 502 }, { status: 502 });
            }),
        );
        const wrapper = await importLink("https://usegalaxy.org/api/short_term_storage/abc");
        await vi.waitFor(() => expect(checks).toBe(1));
        await vi.advanceTimersByTimeAsync(3000);
        await vi.waitFor(() => expect(checks).toBe(2));
        await vi.advanceTimersByTimeAsync(3000);
        await vi.waitFor(() => expect(wrapper.text()).toContain("could not check how the import is going"));
        expect(wrapper.text()).not.toContain("may have expired");
        expect(wrapper.find(".alert-warning").exists()).toBe(true);
    });

    it("keeps the import in upload state without its link", async () => {
        importEndsIn("SUCCESS");
        await importLink("https://usegalaxy.org/api/short_term_storage/abc");
        const items = useUploadState().activeItems.value;
        await vi.waitFor(() => expect(items[0]?.status).toBe("completed"));
        expect(items).toHaveLength(1);
        expect(items[0]).toMatchObject({ uploadMode: "galaxy-link", sourceHost: "usegalaxy.org", taskId: "task1" });
        expect(JSON.stringify(items[0])).not.toContain("short_term_storage");
    });

    it.each([
        ["a deleted", { deleted: true }, true],
        ["an archived", { archived: true }, true],
        ["an active", {}, false],
    ])("for %s target history, blocks the import: %s", async (_, targetHistory, blocked) => {
        const wrapper = await enterLink("https://usegalaxy.org/api/short_term_storage/abc", targetHistory);
        const button = wrapper.find('[data-description="galaxy link import"]');
        expect(button.attributes("aria-disabled") === "true").toBe(blocked);
    });

    it("links the history the items went to, even after the target changes", async () => {
        importEndsIn("SUCCESS");
        const wrapper = await importLink("https://usegalaxy.org/api/short_term_storage/abc");
        await vi.waitFor(() => expect(wrapper.text()).toContain("Done!"));
        await wrapper.setProps({ targetHistoryId: "hist_2" } as never);
        expect(wrapper.findComponent({ name: "SwitchToHistoryLink" }).props("historyId")).toBe("hist_1");
    });
});

const SOURCE = "https://usegalaxy.eu";
const UUID_1 = "0f8fad5b-d9cb-469f-a165-70867728950e";
const UUID_2 = "7c9e6679-7425-40de-944b-e07fc1f90ae7";
const SERVERS = [
    { label: "Europe", url: "https://usegalaxy.eu" },
    { label: "Here", url: window.location.origin },
    { label: "Australia", url: "https://usegalaxy.org.au/" },
];

interface Opened {
    url: URL;
    name?: string;
    features?: string;
}

let popupClose: ReturnType<typeof vi.spyOn>;

// The default popup is this window, so messages from it pass the source check; closing it is only recorded.
function mockPopup(popup: unknown = window) {
    const opened: Opened[] = [];
    popupClose = vi.spyOn(window, "close").mockImplementation(() => {});
    vi.spyOn(window, "open").mockImplementation((url, name, features) => {
        opened.push({ url: new URL(String(url)), name, features });
        return popup as Window;
    });
    return opened;
}

function nonceOf(opened: Opened[]) {
    return opened.at(-1)!.url.searchParams.get("nonce")!;
}

function send(data: unknown, { origin = SOURCE, source = window as MessageEventSource | null } = {}) {
    window.dispatchEvent(new MessageEvent("message", { data, origin, source }));
}

function hello(nonce: string, root = `${SOURCE}/`) {
    return { type: "galaxy-picker/hello", protocol: 1, version: "27.0", root, nonce };
}

function result(nonce: string, links: string[], failed = 0) {
    return {
        type: "galaxy-picker/result",
        protocol: 1,
        nonce,
        items: links.map((link, index) => ({ type: "dataset", name: `item ${index + 1}`, link })),
        failed,
    };
}

async function mountChooser() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    const localVue = getLocalVue();
    const wrapper = mount(GalaxyLinkImport as object, {
        props: { method: { id: "galaxy-link" }, targetHistoryId: "hist_1" },
        global: { ...withPlugins(localVue, pinia), stubs: { ...localVue.stubs, SwitchToHistoryLink: true } },
    });
    mountedChoosers.push(wrapper);
    await flushPromises();
    return wrapper;
}

async function chooseOther(wrapper: VueWrapper, url: string) {
    await wrapper.find('[data-description="galaxy picker server"]').setValue("other");
    await wrapper.find('[data-description="galaxy picker url"]').setValue(url);
}

let mountedChoosers: VueWrapper[] = [];

describe("GalaxyLinkImport, choosing from another Galaxy", () => {
    beforeEach(() => {
        localStorage.clear();
        setMockConfig({ another_galaxy_servers: SERVERS });
    });

    afterEach(() => {
        mountedChoosers.forEach((wrapper) => wrapper.unmount());
        mountedChoosers = [];
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    it("offers the configured servers but not this one, then any other Galaxy", async () => {
        const wrapper = await mountChooser();
        const options = wrapper.findAll('[data-description="galaxy picker server"] option').map((o) => o.text());
        expect(options).toEqual(["Europe", "Australia", "Other Galaxy..."]);
        expect(wrapper.find('[data-description="galaxy picker open"]').text()).toBe("Choose from usegalaxy.eu");
    });

    it("drops a configured server with an invalid address, with a warning", async () => {
        setMockConfig({ another_galaxy_servers: [...SERVERS, { label: "Broken", url: "ftp://example.org" }] });
        const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
        const wrapper = await mountChooser();
        const options = wrapper.findAll('[data-description="galaxy picker server"] option').map((o) => o.text());
        expect(options).toEqual(["Europe", "Australia", "Other Galaxy..."]);
        expect(warnSpy.mock.calls.map(([message]) => String(message))).toEqual([expect.stringContaining('"Broken"')]);
    });

    it.each([
        ["galaxy.example.org", "https://galaxy.example.org/"],
        ["https://galaxy.example.org/galaxy", "https://galaxy.example.org/galaxy/"],
        ["https://xn--bcher-kva.example", "https://xn--bcher-kva.example/"],
        ["http://localhost:8080", "http://localhost:8080/"],
        ["https://bücher.example", null],
        ["http://galaxy.example.org", null],
        ["https://user@galaxy.example.org", null],
    ])("reads the address %s as %s", async (typed, root) => {
        const wrapper = await mountChooser();
        await chooseOther(wrapper, typed);
        const button = wrapper.find('[data-description="galaxy picker open"]');
        expect(button.attributes("aria-disabled") === "true").toBe(root === null);
        if (root) {
            expect(wrapper.text()).toContain(`Opens ${root}`);
        } else {
            expect(wrapper.text()).toContain("starts with https://");
        }
    });

    it("opens the picker in a popup that knows where to answer", async () => {
        const opened = mockPopup();
        const wrapper = await mountChooser();
        await chooseOther(wrapper, "https://galaxy.example.org/galaxy/");
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        const { url, name, features } = opened[0]!;
        expect(`${url.origin}${url.pathname}`).toBe("https://galaxy.example.org/galaxy/pick/another-galaxy");
        expect(url.searchParams.get("return")).toBe(window.location.origin);
        expect(url.searchParams.get("hide_masthead")).toBe("true");
        expect(nonceOf(opened)).toMatch(/^[0-9a-f]{32}$/);
        expect(name).toBe("galaxy-picker");
        expect(features).toContain("popup");
        expect(features).not.toContain("noopener");
        expect(JSON.parse(localStorage.getItem("galaxy-link-import-recent-servers")!)).toEqual([
            "https://galaxy.example.org/galaxy/",
        ]);
    });

    it("says so when the browser blocks the popup", async () => {
        mockPopup(null);
        const wrapper = await mountChooser();
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        expect(wrapper.find('[data-description="galaxy picker blocked"]').exists()).toBe(true);
    });

    it("imports each item the picker sends, one row each", async () => {
        const bodies = importEndsIn("SUCCESS");
        const opened = mockPopup();
        const wrapper = await mountChooser();
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        const nonce = nonceOf(opened);
        const links = [`${SOURCE}/api/short_term_storage/${UUID_1}`, `${SOURCE}/api/short_term_storage/${UUID_2}`];
        send(hello(nonce));
        send(result(nonce, links));
        await vi.waitFor(() => expect(bodies).toHaveLength(2));
        expect(popupClose).toHaveBeenCalled();
        expect(bodies.map((body) => body.store_content_uri)).toEqual(links);
        const rows = wrapper.findAll('[data-description="galaxy picker import item"]');
        expect(rows.map((row) => row.text())).toEqual([
            expect.stringContaining("item 1"),
            expect.stringContaining("item 2"),
        ]);
        await vi.waitFor(() => expect(wrapper.text()).toContain("Imported"));
    });

    it("does not import the items again when the user switches to Paste a link and back", async () => {
        const bodies = importEndsIn("SUCCESS");
        const opened = mockPopup();
        const wrapper = await mountChooser();
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        const nonce = nonceOf(opened);
        send(hello(nonce));
        send(
            result(nonce, [`${SOURCE}/api/short_term_storage/${UUID_1}`, `${SOURCE}/api/short_term_storage/${UUID_2}`]),
        );
        await vi.waitFor(() =>
            expect(wrapper.findAll(ITEM).map((row) => row.text())).toEqual([
                expect.stringContaining("Imported"),
                expect.stringContaining("Imported"),
            ]),
        );
        const mode = '[data-description="galaxy link import mode"]';
        await wrapper.find(`${mode} input[value="paste"]`).setValue(true);
        await wrapper.find(`${mode} input[value="choose"]`).setValue(true);
        await wrapper.find(`${mode} input[value="paste"]`).setValue(true);
        await wrapper.find(`${mode} input[value="choose"]`).setValue(true);
        await vi.waitFor(() =>
            expect(wrapper.findAll(ITEM).map((row) => row.text())).toEqual([
                expect.stringContaining("Imported"),
                expect.stringContaining("Imported"),
            ]),
        );
        expect(bodies).toHaveLength(2);
    });

    it("shows on its row why an import could not be started", async () => {
        server.use(
            http.post(IMPORT, ({ response }) =>
                response("4XX").json({ err_msg: "History is not writable", err_code: 403002 }, { status: 403 }),
            ),
        );
        const opened = mockPopup();
        const wrapper = await mountChooser();
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        const nonce = nonceOf(opened);
        send(hello(nonce));
        send(result(nonce, [`${SOURCE}/api/short_term_storage/${UUID_1}`]));
        await vi.waitFor(() => expect(wrapper.find(ITEM).text()).toContain("History is not writable"));
        expect(wrapper.find(ITEM).find('[data-description="loading message"]').exists()).toBe(false);
    });

    it.each([
        ["another origin", { origin: "https://evil.example" }],
        ["another window", { source: new MessageChannel().port1 }],
    ])("ignores a result from %s", async (_, from) => {
        const bodies = importEndsIn("SUCCESS");
        const opened = mockPopup();
        const wrapper = await mountChooser();
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        const nonce = nonceOf(opened);
        send(hello(nonce));
        send(result(nonce, [`${SOURCE}/api/short_term_storage/${UUID_1}`]), from);
        await flushPromises();
        expect(bodies).toHaveLength(0);
        expect(popupClose).not.toHaveBeenCalled();
        expect(wrapper.find('[data-description="galaxy picker waiting"]').exists()).toBe(true);
    });

    it.each([
        [1, "1 item could not be exported"],
        [2, "2 items could not be exported"],
    ])("says when %i chosen items did not arrive and leaves the reasons open in the popup", async (failed, text) => {
        importEndsIn("SUCCESS");
        const opened = mockPopup();
        const wrapper = await mountChooser();
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        const nonce = nonceOf(opened);
        send(hello(nonce));
        send(result(nonce, [`${SOURCE}/api/short_term_storage/${UUID_1}`], failed));
        await flushPromises();
        expect(wrapper.findAll('[data-description="galaxy picker import item"]')).toHaveLength(1);
        const notice = wrapper.find('[data-description="galaxy picker some failed"]');
        expect(notice.text()).toContain(text);
        expect(notice.text()).toContain("The usegalaxy.eu window lists why");
        expect(popupClose).not.toHaveBeenCalled();
        expect(wrapper.find('[data-description="galaxy picker waiting"]').exists()).toBe(false);
    });

    it("says the items failed, not that nothing was chosen, when none of them arrived", async () => {
        const opened = mockPopup();
        const wrapper = await mountChooser();
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        const nonce = nonceOf(opened);
        send(hello(nonce));
        send(result(nonce, [], 2));
        await flushPromises();
        expect(wrapper.findAll('[data-description="galaxy picker import item"]')).toHaveLength(0);
        expect(wrapper.find('[data-description="galaxy picker some failed"]').text()).toContain(
            "2 items could not be exported",
        );
        expect(wrapper.find('[data-description="galaxy picker cancelled"]').exists()).toBe(false);
        expect(popupClose).not.toHaveBeenCalled();
    });

    it("ignores a result with another nonce, or before the picker said hello", async () => {
        const bodies = importEndsIn("SUCCESS");
        const opened = mockPopup();
        const wrapper = await mountChooser();
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        const nonce = nonceOf(opened);
        const links = [`${SOURCE}/api/short_term_storage/${UUID_1}`];
        send(result(nonce, links));
        send(hello("f".repeat(32)));
        send(result(nonce, links));
        send(hello(nonce));
        send(result("f".repeat(32), links));
        await flushPromises();
        expect(bodies).toHaveLength(0);
        send(result(nonce, links));
        await vi.waitFor(() => expect(bodies).toHaveLength(1));
        send(result(nonce, links));
        await flushPromises();
        expect(bodies).toHaveLength(1);
    });

    it("checks links against the root the picker reports, not the address typed", async () => {
        const bodies = importEndsIn("SUCCESS");
        const opened = mockPopup();
        const wrapper = await mountChooser();
        await chooseOther(wrapper, `${SOURCE}/datasets/list`);
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        const nonce = nonceOf(opened);
        send(hello(nonce, "https://other.example/"));
        send(hello(nonce, `${SOURCE}/`));
        send(result(nonce, [`${SOURCE}/api/short_term_storage/${UUID_1}`]));
        await vi.waitFor(() => expect(bodies).toHaveLength(1));
    });

    it("imports nothing when any link is not from the picker's Galaxy", async () => {
        const bodies = importEndsIn("SUCCESS");
        const opened = mockPopup();
        const wrapper = await mountChooser();
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        const nonce = nonceOf(opened);
        send(hello(nonce, `${SOURCE}/galaxy/`));
        send(
            result(nonce, [
                `${SOURCE}/galaxy/api/short_term_storage/${UUID_1}`,
                `${SOURCE}/api/short_term_storage/${UUID_2}`,
            ]),
        );
        await flushPromises();
        expect(wrapper.find('[data-description="galaxy picker bad links"]').exists()).toBe(true);
        expect(popupClose).toHaveBeenCalled();
        expect(bodies).toHaveLength(0);
    });

    it("points to Paste a link when the picker does not answer within 15 seconds", async () => {
        vi.useFakeTimers();
        const opened = mockPopup();
        const wrapper = await mountChooser();
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        await vi.advanceTimersByTimeAsync(14000);
        expect(wrapper.find('[data-description="galaxy picker no answer"]').exists()).toBe(false);
        await vi.advanceTimersByTimeAsync(1000);
        const notice = wrapper.find('[data-description="galaxy picker no answer"]');
        expect(notice.text()).toContain("No answer from usegalaxy.eu yet");
        send(hello(nonceOf(opened)));
        await flushPromises();
        expect(wrapper.find('[data-description="galaxy picker no answer"]').exists()).toBe(false);
    });

    it("points to Paste a link when the popup closes without an answer", async () => {
        vi.useFakeTimers();
        mockPopup({ closed: true });
        const wrapper = await mountChooser();
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        await vi.advanceTimersByTimeAsync(1000);
        const notice = wrapper.find('[data-description="galaxy picker no answer"]');
        expect(notice.exists()).toBe(true);
        await notice.find("button").trigger("click");
        expect(wrapper.find('[data-description="galaxy link input"]').exists()).toBe(true);
        expect(wrapper.find('[data-description="galaxy picker waiting"]').exists()).toBe(false);
    });

    it("stops waiting when the user chooses nothing", async () => {
        const opened = mockPopup();
        const wrapper = await mountChooser();
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        send({ type: "galaxy-picker/cancel", nonce: nonceOf(opened) });
        await flushPromises();
        expect(wrapper.find('[data-description="galaxy picker cancelled"]').exists()).toBe(true);
        expect(popupClose).toHaveBeenCalled();
        expect(wrapper.find('[data-description="galaxy picker waiting"]').exists()).toBe(false);
    });

    it("says nothing was chosen when the user closes the popup after it answered", async () => {
        vi.useFakeTimers();
        const opened = mockPopup();
        const closed = vi.spyOn(window, "closed", "get").mockReturnValue(false);
        const wrapper = await mountChooser();
        await wrapper.find('[data-description="galaxy picker open"]').trigger("click");
        send(hello(nonceOf(opened)));
        await vi.advanceTimersByTimeAsync(1000);
        expect(wrapper.find('[data-description="galaxy picker waiting"]').exists()).toBe(true);
        closed.mockReturnValue(true);
        await vi.advanceTimersByTimeAsync(1000);
        expect(wrapper.find('[data-description="galaxy picker waiting"]').exists()).toBe(false);
        expect(wrapper.find('[data-description="galaxy picker cancelled"]').text()).toContain(
            "Nothing was chosen on usegalaxy.eu",
        );
        expect(wrapper.find('[data-description="galaxy picker no answer"]').exists()).toBe(false);
    });
});
