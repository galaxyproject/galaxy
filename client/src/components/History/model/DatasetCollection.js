/**
 * Our API is very inconsistent which makes re-using components difficult.
 * This wrapper is supposed to make sub-collections look reasonably close to
 * the dataset collections that are loose in the content results so
 * we can pass them to the same components.
 */

import { Content } from "./Content";
import { JobStateSummary } from "./JobStateSummary";
import { scrubModelProps } from "utils/safeAssign";

export class DatasetCollection extends Content {
    loadProps(raw = {}) {
        if (!raw.contents_url) {
            throw new Error("missing contents_url", raw);
        }
        super.loadProps(raw);
    }

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
        return this.jobSummary.state;
    }

    get jobSummary() {
        return Object.freeze(new JobStateSummary(this));
    }

    /** Whether all elements in the collection have the same datatype.
     *  @return {Boolean}
     */
    get isHomogeneous() {
        return this.elements_datatypes.length == 1;
    }

    /** Gets the datatype shared by all elements or an empty
     * string if the collection has mixed types of datasets.
     *  @return {String}
     */
    get homogeneousDatatype() {
        return this.isHomogeneous ? this.elements_datatypes[0] : "";
    }

    clone() {
        const newProps = cleanDscProps(this);
        return new DatasetCollection(newProps);
    }

    patch(newProps) {
        const cleanProps = cleanDscProps({ ...this, ...newProps });
        return new DatasetCollection(cleanProps);
    }

    equals(other) {
        return DatasetCollection.equals(this, other);
    }
}

DatasetCollection.equals = function (a, b) {
    return JSON.stringify(a) == JSON.stringify(b);
};

const scrubber = scrubModelProps(DatasetCollection);
export const cleanDscProps = (props = {}) => {
    const cleanProps = JSON.parse(JSON.stringify(props));
    return scrubber(cleanProps);
};
