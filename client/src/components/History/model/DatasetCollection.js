/**
 * Our API is very inconsistent which makes re-using components difficult.
 * This wrapper is supposed to make sub-collections look reasonably close to
 * the dataset collections that are loose in the content results so
 * we can pass them to the same components.
 */

import { Content } from "./Content";
import { JobStateSummary } from "./JobStateSummary";
import { objectNeedsProps } from "utils/objectNeedsProps";

export class DatasetCollection extends Content {
    loadProps(raw = {}) {
        if (!raw.contents_url) {
            // console.log("ouch", raw);
            throw new Error("missing contents_url", raw);
        }
        super.loadProps(raw);
    }

    // number of contained contents
    // Need to do some manual handling, because once again, the API is
    // inconsistent, element_count not returned in the case of a pair. It
    // should be two, but we need to add that value in.
    get totalElements() {
        if ("element_count" in this) {
            return this.element_count;
        }

        if (this.collection_type == "paired") {
            return 2;
        }

        return undefined;
    }

    // text for UI
    get collectionCountDescription() {
        const ct = this.totalElements;
        return ct == 1 ? "with 1 item" : `with ${ct} items`;
    }

    // text for UI
    get collectionType() {
        if (this.collection_type) {
            switch (this.collection_type) {
                case "list":
                    return "list";
                case "paired":
                    return "dataset pair";
                case "list:paired":
                    return "list of pairs";
                default:
                    return "nested list";
            }
        }
        return null;
    }

    // amalgam state value
    get state() {
        return this.jobSummary.state || this.populated_state;
    }

    get jobSummary() {
        return new JobStateSummary(this);
    }
}

DatasetCollection.equals = function (a, b) {
    return JSON.stringify(a) == JSON.stringify(b);
};

// determines if we have enough props to make a DSC
DatasetCollection.isValidCollectionProps = objectNeedsProps(["parent_url", "type_id", "id", "history_content_type"]);
