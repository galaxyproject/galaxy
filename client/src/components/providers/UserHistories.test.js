import { createPinia } from "pinia";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { useHistoryStore } from "stores/historyStore";
import UserHistories from "./UserHistories";
import {
    getHistoryList,
    getHistoryByIdFromServer,
    getCurrentHistoryFromServer,
    setCurrentHistoryOnServer,
    createAndSelectNewHistory,
    updateHistoryFields,
    deleteHistoryById,
} from "stores/services/history.services";

jest.mock("app");
jest.mock("stores/services/history.services");

const localVue = getLocalVue();

// test user data
const fakeUser = { id: 123234, name: "Bob" };
const createdHistory = { id: 666, name: "I am new" };

// test store data
let currentHistoryId;
let histories;
const setTestData = () => {
    const ids = [1, 2, 3, 4];
    currentHistoryId = ids[0];
    histories = ids.map((i) => ({ id: i, name: `History #${i}` }));
};

// mock store queries
getHistoryList.mockImplementation(async () => {
    return [...histories];
});
getCurrentHistoryFromServer.mockImplementation(async () => {
    return histories.find((o) => o.id == currentHistoryId);
});
getHistoryByIdFromServer.mockImplementation(async (id) => {
    return histories.find((o) => o.id == id);
});
createAndSelectNewHistory.mockImplementation(async () => {
    histories.push(createdHistory);
    return Object.assign({}, createdHistory);
});
setCurrentHistoryOnServer.mockImplementation(async (id) => {
    currentHistoryId = id;
    const result = histories.find((h) => h.id == id);
    return Object.assign({}, result);
});
updateHistoryFields.mockImplementation(async (id, payload = {}) => {
    const existingHistory = histories.find((h) => h.id == id);
    return { ...existingHistory, ...payload };
});
deleteHistoryById.mockImplementation(async (id) => {
    return histories.find((h) => h.id == id);
});

// user histories provider test cases
describe("UserHistories", () => {
    let wrapper;
    let slotProps;
    let historyStore;

    beforeEach(async () => {
        setTestData();
        const pinia = createPinia();

        wrapper = shallowMount(UserHistories, {
            localVue,
            propsData: {
                user: fakeUser,
            },
            scopedSlots: {
                default(props) {
                    slotProps = props;
                },
            },
            pinia,
        });

        historyStore = useHistoryStore();
        historyStore.setHistories(histories);
        historyStore.setCurrentHistoryId(currentHistoryId);
    });

    afterEach(async () => {
        if (wrapper) {
            await wrapper.destroy();
        }
    });

    describe("slotProp values", () => {
        test("histories", async () => {
            const { histories } = slotProps;
            expect(histories).toBeInstanceOf(Array);
            expect(histories.length).toEqual(histories.length);
            histories.forEach((h) => {
                expect(h).toBeInstanceOf(Object);
            });
        });

        test("currentHistory", async () => {
            const { histories, currentHistory } = slotProps;
            expect(currentHistory).toBeInstanceOf(Object);
            expect(histories.find((h) => h.id == currentHistory.id)).toEqual(currentHistory);
        });
    });

    describe("slotProp handlers", () => {
        test("setCurrentHistory", async () => {
            const { setCurrentHistory } = slotProps.handlers;
            expect(setCurrentHistory).toBeInstanceOf(Function);
            // set another history as current
            const nextHistory = histories[1];
            await setCurrentHistory(nextHistory);
            // verify that current history has changed
            const { currentHistory: changedHistory, histories: newHistories } = slotProps;
            expect(changedHistory.id).toEqual(nextHistory.id);
            expect(changedHistory).toBeInstanceOf(Object);
            expect(newHistories.find((h) => h.id == changedHistory.id)).toEqual(changedHistory);
        });

        test("createNewHistory", async () => {
            const { createNewHistory } = slotProps.handlers;
            expect(createNewHistory).toBeInstanceOf(Function);
            // expect initial history id
            expect(slotProps.currentHistory.id).toEqual(histories[0].id);
            // create new history
            await createNewHistory();
            // expect new history id
            expect(slotProps.currentHistory.id).toEqual(createdHistory.id);
        });

        test("updateHistory", async () => {
            const {
                currentHistory,
                handlers: { updateHistory },
            } = slotProps;
            expect(updateHistory).toBeInstanceOf(Function);
            expect(currentHistory).toBeInstanceOf(Object);
            const modifiedHistory = { ...currentHistory, foo: "bar" };
            expect(modifiedHistory.id).toBeDefined();
            await updateHistory(modifiedHistory);
            expect(slotProps.histories.find((h) => h.foo == "bar")).toBeTruthy();
        });

        test("deleteHistory", async () => {
            const {
                currentHistory,
                handlers: { deleteHistory },
            } = slotProps;
            expect(deleteHistory).toBeInstanceOf(Function);
            await deleteHistory(currentHistory);
            expect(slotProps.histories.find((h) => h.id == currentHistory.id)).toBeFalsy();
            expect(slotProps.currentHistory.id).not.toEqual(currentHistory.id);
        });
    });
});
