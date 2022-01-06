import { History } from "components/History/model";
import { SearchParams } from "components/providers/History/SearchParams";
import rawHistory from "./json/History.json";
import rawHistoryContent from "./json/historyContent.json";

// doctor the sample content
export const testHistoryContent = rawHistoryContent.map((item) => {
    item.history_id = rawHistory.id;
    return item;
});

// doctor the sample history
export const testHistory = new History({
    ...rawHistory,
    hid_counter: testHistoryContent[0].hid + 1,
});

// simplified filter simlates server-side complete set
export const serverContent = (filters = new SearchParams()) => {
    return testHistoryContent.filter((o) => {
        if (!filters.showDeleted && o.deleted) {
            return false;
        }
        if (!filters.showHidden && !o.visible) {
            return false;
        }
        return true;
    });
};
