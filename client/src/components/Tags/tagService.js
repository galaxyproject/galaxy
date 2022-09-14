/**
 * Generates a service object used by the tagging component to save, delete and
 * lookup potential tag options for the autocomplete feature. Standard typeahead
 * debouncing and ajax cancelling functionality is also provided here, though an
 * argument can be made that it more properly belongs in the component that is
 * handling the inputs.
 *
 * TODO: convert the associated python endpoint to a legit json REST service
 */
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import { createTag } from "./model";
import { Subject } from "rxjs";
import { map, filter, debounceTime, switchMap, distinctUntilChanged } from "rxjs/operators";

export class TagService {
    constructor({ id, itemClass, context, debounceInterval = 150 }) {
        this.id = id;
        this.itemClass = itemClass;
        this.context = context;
        this.debounceInterval = debounceInterval;

        // Buffer for autocomplete text changes
        this._searchText = new Subject();
    }

    /**
     * Autocomplete observable. Subscribe to this object to get updates to
     * matching autocomplete results as the autocompleteSearchText property is
     * changed
     */
    get autocompleteOptions() {
        return this._searchText.pipe(
            map((txt) => txt.replace("name:", "")),
            filter((txt) => txt.length),
            debounceTime(this.debounceInterval),
            distinctUntilChanged(),
            switchMap((txt) => this.autocomplete(txt))
        );
    }

    /**
     * Set this property to start process of retrieving autocomplete results.
     */
    set autocompleteSearchText(txt) {
        this._searchText.next(txt);
    }

    /**
     * Save tag, input can be text string or tag model
     * @param {string|Tag} tag
     * @returns Promise yielding new tag model
     */
    async save(rawTag) {
        const { id, itemClass, context } = this;
        const tag = createTag(rawTag);
        if (!tag.valid) {
            throw new Error("Invalid tag");
        }
        const url = `${getAppRoot()}tag/add_tag_async`;
        const config = {
            params: { item_id: id, item_class: itemClass, context: context, new_tag: tag.text },
        };
        const response = await axios.get(url, config);
        if (response.status !== 200) {
            throw new Error(`Unable to save tag: ${tag}`);
        }
        return createTag(tag);
    }

    /**
     * Delete tag, input can be text string or tag model
     * @param {string|Tag} tag
     * @returns Promise yielding deleted tag model
     */
    async delete(rawTag) {
        const { id, itemClass, context } = this;
        const tag = createTag(rawTag);
        const url = `${getAppRoot()}tag/remove_tag_async`;
        const config = { params: { item_id: id, item_class: itemClass, context: context, tag_name: tag.text } };
        const response = await axios.get(url, config);
        if (response.status !== 200) {
            throw new Error(`Unable to delete tag: ${tag}`);
        }
        return tag;
    }

    /**
     * Looks up autocomplete options based on search text
     * @param {string} searchText
     * @returns Promise yielding an array of tag models
     */
    async autocomplete(searchText) {
        const { id, itemClass } = this;
        const url = `${getAppRoot()}tag/tag_autocomplete_data`;
        const config = { params: { item_id: id, item_class: itemClass, q: searchText } };
        const response = await axios.get(url, config);
        if (response.status !== 200) {
            throw new Error(`Unable to retrieve autocomplete tags for search string: ${searchText}`);
        }
        return parseAutocompleteResults(response.data).map(createTag);
    }
}

/**
 * Utility function parser for the archaic result format in the current API. See
 * testData/autocompleteResponse.txt for a sample.
 * @param {string} rawResponse
 */
export function parseAutocompleteResults(rawResponse) {
    return rawResponse
        .split("\n")
        .filter((line) => line.includes("|"))
        .map((line) => line.split("|")[0])
        .filter((label) => label.length)
        .filter((label) => label !== "#Header");
}
