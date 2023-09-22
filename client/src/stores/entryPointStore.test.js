import { setActivePinia, createPinia } from "pinia";
import { useEntryPointStore } from "./entryPointStore";
import flushPromises from "flush-promises";
import testInteractiveToolsResponse from "../components/InteractiveTools/testData/testInteractiveToolsResponse";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";

describe("stores/EntryPointStore", () => {
    let axiosMock;
    let store;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        setActivePinia(createPinia());
        axiosMock.onGet("/api/entry_points", { params: { running: true } }).reply(200, testInteractiveToolsResponse);
        store = useEntryPointStore();
        store.ensurePollingEntryPoints();
        await flushPromises();
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("polls", async () => {
        expect(store.entryPoints.length).toBe(2);
    });
    it("stops polling", async () => {
        expect(store.pollTimeout >= 0).toBeTruthy();
        store.stopPollingEntryPoints();
        expect(store.pollTimeout === undefined).toBeTruthy();
    });
    it("performs a partial update", async () => {
        store.stopPollingEntryPoints();
        const updateData = [
            {
                model_class: "InteractiveToolEntryPoint",
                id: "b887d74393f85b6d",
                job_id: "52e496b945151ee8",
                name: "Oh there you go, bringing class into it again.",
                created_time: "2020-01-24T15:59:22.406480",
                modified_time: "2020-02-24T15:59:24.757453",
                output_datasets_ids: ["4e9e0c7225b0bb81"],
                target: "http://b887d74393f85b6d-b1fd3f42331a49c1b3d8a4d1b27240b8.interactivetoolentrypoint.interactivetool.localhost:8080/loginapikey/oleg",
            },
        ];
        store.updateEntryPoints(updateData);
        expect(store.entryPoints.length).toBe(1);
        expect(store.entryPoints[0].name === "Oh there you go, bringing class into it again.").toBeTruthy();
        expect(store.entryPoints[0].active).toBeTruthy();
    });
    it("removes an entry point of given id", async () => {
        let entryPointForId = store.entryPoints.filter((item) => item.id === "52e496b945151ee8");
        expect(entryPointForId.length).toBe(1);
        store.removeEntryPoint("52e496b945151ee8");
        entryPointForId = store.entryPoints.filter((item) => item.id === "52e496b945151ee8");
        expect(entryPointForId.length).toBe(0);
    });
    it("retrieves entry point for a given job", async () => {
        const entryPointForJob = store.entryPointsForJob("6fc9fbb81c497f69");
        expect(entryPointForJob.length).toBe(1);
        expect(entryPointForJob[0].id === "52e496b945151ee8").toBeTruthy();
        expect(entryPointForJob[0].active).toBeTruthy();
    });
    it("retrieves entry points for a given hda", async () => {
        const entryPointForHda = store.entryPointsForHda("4e9e0c7225b0bb81");
        expect(entryPointForHda.length).toBe(1);
        expect(entryPointForHda[0].id === "52e496b945151ee8").toBeTruthy();
        expect(entryPointForHda[0].active).toBeTruthy();
    });
});
