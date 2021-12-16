import Vuex from "vuex";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue, wait, waitForLifecyleEvent, watchForChange } from "jest/helpers";
import { historyStore } from "components/History/model/historyStore";
import { History } from "components/History/model/History";
import UserHistories from "./UserHistories";

// #region Test Data

let historySummaries;
let fullHistories;
let currentHistoryId;

const resetTestData = () => {
    const ids = [1, 2, 3, 4];
    currentHistoryId = ids[0];
    historySummaries = ids.map((i) => ({ id: i, name: `History #${i}` }));
    fullHistories = historySummaries.map((h) => ({ ...h, detailView: true }));
};

const fakeUser = { id: 123234, name: "Bob" };

// #endregion

// #region Mock server responses

import {
    getHistoryList,
    getHistoryById,
    getCurrentHistoryFromServer,
    setCurrentHistoryOnServer,
    createNewHistory,
    updateHistoryFields,
    deleteHistoryById,
} from "components/History/model/queries";

jest.mock("app");
jest.mock("components/providers/History/caching");
jest.mock("components/History/model/queries");

const maxServerDelay = 60;
const serverDelay = async (min = 0, max = maxServerDelay) => {
    const delay = min + Math.random() * (max - min);
    await wait(delay);
};

getHistoryList.mockImplementation(async () => {
    await serverDelay();
    return [...historySummaries];
});

getCurrentHistoryFromServer.mockImplementation(async () => {
    await serverDelay();
    return fullHistories.find((o) => o.id == currentHistoryId);
});

getHistoryById.mockImplementation(async (id) => {
    await serverDelay();
    return fullHistories.find((o) => o.id == id);
});

const createdHistory = { id: 666, name: "I am new" };
createNewHistory.mockImplementation(async () => {
    await serverDelay();
    historySummaries.push(createdHistory);
    const newFullHistory = { ...createdHistory, detailView: true };
    fullHistories.push(newFullHistory);
    return Object.assign({}, newFullHistory);
});

setCurrentHistoryOnServer.mockImplementation(async (id) => {
    await serverDelay();
    currentHistoryId = id;
    const result = fullHistories.find((h) => h.id == id);
    return Object.assign({}, result);
});

updateHistoryFields.mockImplementation(async (id, payload = {}) => {
    await serverDelay();
    const existingHistory = fullHistories.find((h) => h.id == id);
    return { ...existingHistory, ...payload };
});

deleteHistoryById.mockImplementation(async (id) => {
    await serverDelay();
    return fullHistories.find((h) => h.id == id);
});

// #endregion

// #region Mounting

const localVue = getLocalVue();

// Generate store for tesint, just need the one module we talk to
const historiesStore = new Vuex.Store({
    modules: {
        betaHistory: historyStore,
    },
});

// #endregion

describe("UserHistories", () => {
    let wrapper;
    let slotProps;

    beforeEach(async () => {
        resetTestData();
        wrapper = shallowMount(UserHistories, {
            localVue,
            store: historiesStore,
            propsData: {
                user: fakeUser,
            },
            scopedSlots: {
                default(props) {
                    slotProps = props;
                },
            },
        });
        await waitForLifecyleEvent(wrapper.vm, "updated");
    });

    afterEach(async () => {
        historiesStore.dispatch("betaHistory/reset");
        if (wrapper) {
            await wrapper.destroy();
        }
    });

    describe("slotProps: values", () => {
        test("histories", async () => {
            const { histories } = slotProps;
            expect(histories).toBeInstanceOf(Array);
            expect(histories.length).toEqual(historySummaries.length);
            histories.forEach((h) => {
                expect(h).toBeInstanceOf(History);
            });
        });

        test("currentHistory", async () => {
            const { histories, currentHistory } = slotProps;
            expect(currentHistory).toBeInstanceOf(History);
            expect(histories.find((h) => h.id == currentHistory.id)).toEqual(currentHistory);
        });
    });

    describe("slotProp handlers", () => {
        test("setCurrentHistory", async () => {
            const { setCurrentHistory } = slotProps.handlers;
            expect(setCurrentHistory).toBeInstanceOf(Function);

            // set another history as current
            const nextHistory = historySummaries[1];
            setCurrentHistory(nextHistory);

            await watchForChange({
                vm: wrapper.vm,
                propName: "currentHistory",
                label: "currenntHistoryChange",
            });

            // wait for it to register
            const { currentHistory: changedHistory, histories: newHistories } = slotProps;
            expect(changedHistory.id).toEqual(nextHistory.id);
            expect(changedHistory).toBeInstanceOf(History);
            expect(newHistories.find((h) => h.id == changedHistory.id)).toEqual(changedHistory);
        });

        test("createNewHistory", async () => {
            const { createNewHistory } = slotProps.handlers;
            expect(createNewHistory).toBeInstanceOf(Function);

            // create new history
            await createNewHistory();

            await watchForChange({
                vm: wrapper.vm,
                propName: "currentHistory",
            });

            // wait for it to come out of the slot
            expect(slotProps.currentHistory.id).toEqual(createdHistory.id);
        });

        test("updateHistory", async () => {
            const {
                currentHistory,
                handlers: { updateHistory },
            } = slotProps;
            expect(updateHistory).toBeInstanceOf(Function);
            expect(currentHistory).toBeInstanceOf(History);
            const modifiedHistory = { ...currentHistory, foo: "bar" };

            expect(modifiedHistory.id).toBeDefined();
            await updateHistory(modifiedHistory);
            await waitForLifecyleEvent(wrapper.vm, "updated");

            expect(slotProps.histories.find((h) => h.foo == "bar")).toBeTruthy();
        });

        test("deleteHistory", async () => {
            const {
                currentHistory,
                handlers: { deleteHistory },
            } = slotProps;

            expect(deleteHistory).toBeInstanceOf(Function);

            await deleteHistory(currentHistory);
            await waitForLifecyleEvent(wrapper.vm, "updated");
            expect(slotProps.histories.find((h) => h.id == currentHistory.id)).toBeFalsy();
            expect(slotProps.currentHistory.id).not.toEqual(currentHistory.id);
        });
    });
});
