/**
 * Replacement for skiplist, aggregates history contents as updates come in,
 * then sorts the keys of the map on demand. Also can find the closest map key
 * to a given target value (cursor).
 */

export class UpdateMap extends Map {
    sortKeys(direction) {
        const entries = Array.from(this.entries());
        if (entries.length == 0) return;
        const intDirection = direction == "asc" ? 1 : -1;
        const sortFn = (a, b) => intDirection * (a[0] - b[0]);
        const newContents = entries.sort(sortFn);
        this.replaceEntries(newContents);
    }

    replaceEntries(entries) {
        this.clear();
        for (const [key, val] of entries) {
            this.set(key, val);
        }
    }

    findClosestKey(target) {
        let minDist = Infinity;
        let closestKey = null;
        let closestIndex = null;
        let index = 0;

        for (const [key] of this) {
            // This is an exact match. We're done here.
            if (key == target) {
                closestKey = key;
                closestIndex = index;
                break;
            }

            // How far is this key from our target cursor?
            const dist = Math.abs(key - target);

            // because the incoming sourceMap is pre-sorted by key we can stop looping
            // when the distance is getting larger, this means we're moving further
            // away from the right answer which we already found
            if (dist > minDist) {
                break;
            }

            if (dist < minDist) {
                minDist = dist;
                closestKey = key;
                closestIndex = index;
            }

            index++;
        }

        return { key: closestKey, index: closestIndex };
    }
}
