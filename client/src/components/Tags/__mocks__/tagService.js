/**
 * Generates a service object used by the tagging component to save, delete and
 * lookup potential tag options for the autocomplete feature. Standard typeahead
 * debouncing and ajax cancelling functionality is also provided here, though an
 * argument can be made that it more properly belongs in the component that is
 * handling the inputs.
 *
 * TODO: convert the associated python endpoint to a legit json REST service
 */

import { createTag } from "../model";
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

    async save(tag) {
        return createTag(tag);
    }

    async delete(tag) {
        return createTag(tag);
    }

    async autocomplete(txt) {
        return [txt].map(createTag);
    }
}
