/**
 * Given a collection, tracks cache changes to the object.
 *
 * Dataset collections are stored in two places depending on how deeply nested
 * it is in the tree. At the top level are root dataset collections which are
 * elements of a history's contents. These source their data from the content
 * cache. Then inside a dataset collection, it's possible to nest other
 * collections arbitrarily, these collections come from the collections cache
 * and the api does not necessarily deliver the same fields for both scenarios,
 * but we run both raw objects into a DatasetCollection model class.
 */

import { of } from "rxjs";
import { map, pluck, switchMap, distinctUntilChanged } from "rxjs/operators";
import { whenAny } from "utils/observable/whenAny";
import { monitorContentQuery, monitorDscQuery } from "components/providers/History/caching";
import { DatasetCollection } from "components/History/model/DatasetCollection";
import deepEqual from "deep-equal";

// passed object should have a pouch _id for monitoring
const hasPouchId = (o) => "_id" in o;

export default {
    props: {
        collection: { type: Object, required: true, validator: hasPouchId },
        isRoot: { type: Boolean, required: true },
    },
    data() {
        return {
            raw: this.collection,
        };
    },
    computed: {
        dsc() {
            const cleanObj = JSON.parse(JSON.stringify(this.raw));
            return new DatasetCollection(cleanObj);
        },
    },
    watch: {
        collection(newVal, oldVal) {
            if (newVal && !deepEqual(newVal, oldVal)) {
                this.raw = newVal;
            }
        },
        dsc(newVal, oldVal) {
            if (newVal && !deepEqual(newVal, oldVal)) {
                this.$emit("update:collection", newVal);
            }
        },
    },
    // prettier-ignore
    created() {
        const root$ = this.watch$("isRoot", true).pipe(
            distinctUntilChanged()
        );

        const id$ = this.watch$("collection", true).pipe(
            pluck("_id"),
            distinctUntilChanged()
        );

        const monitor$ = whenAny(id$, root$).pipe(
            switchMap((inputs) => {
                const [_id, isRoot] = inputs;
                const monitorOperator = isRoot ? monitorContentQuery : monitorDscQuery;
                const selector = { _id };
                const request = { selector, offset: 0, limit: 1 };

                return of(request).pipe(
                    monitorOperator(),
                    map((update) => {
                        const { initialMatches = [], doc = null, deleted } = update;
                        if (deleted) {
                            return null;
                        }
                        let updatedDoc = doc;
                        if (initialMatches.length == 1) {
                            updatedDoc = initialMatches[0];
                        }
                        return updatedDoc;
                    }),
                );
            })
        );

        this.$subscribeTo(monitor$, (doc) => {
            this.raw = doc;
        });
    },
    render() {
        return this.$scopedSlots.default({
            dsc: this.dsc,
        });
    },
};
