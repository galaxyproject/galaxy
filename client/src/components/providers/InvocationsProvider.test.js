import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import mockInvocationData from "components/Workflow/test/json/invocation.json";
import { invocationsProvider } from "./InvocationsProvider";

describe("invocationsProvider", () => {
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    describe("fetching invocations without an error", () => {
        it("should make an API call and fire callback", async () => {
            axiosMock
                .onGet("/prefix/api/invocations", { params: { limit: 50, offset: 0, include_terminal: false } })
                .reply(200, [mockInvocationData], { total_matches: "1" });

            const ctx = {
                root: "/prefix/",
                perPage: 50,
                currentPage: 1,
            };
            const extras = {
                include_terminal: false,
            };

            let called = false;
            const callback = function () {
                called = true;
            };
            const promise = invocationsProvider(ctx, callback, extras);
            await promise;
            expect(called).toBeTruthy();
        });
    });
});
