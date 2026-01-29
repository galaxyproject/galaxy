/* classes for reasoning about collection map over state
   null: not a collection?
   NULL_COLLECTION_TYPE_DESCRIPTION: also not a collection. Is there any difference with null ?
   ANY_COLLECTION_TYPE_DESCRIPTION: collection, but will never be mapped over (input has no collection_type)
   CollectionTypeDescription: "normal" collection, with a `collection_type`
*/

export interface CollectionTypeDescriptor {
    isCollection: boolean;
    collectionType: string | null;
    rank: number;
    canMatch(other: CollectionTypeDescriptor): boolean;
    canMapOver(other: CollectionTypeDescriptor): boolean;
    append(other: CollectionTypeDescriptor): CollectionTypeDescriptor;
    equal(other: CollectionTypeDescriptor | null): boolean;
    toString(): string;
    effectiveMapOver(other: CollectionTypeDescriptor): CollectionTypeDescriptor;
}

export const NULL_COLLECTION_TYPE_DESCRIPTION: CollectionTypeDescriptor = {
    isCollection: false,
    collectionType: null,
    rank: 0,
    canMatch: function (_other) {
        return false;
    },
    canMapOver: function () {
        return false;
    },
    toString: function () {
        return "NullCollectionType[]";
    },
    append: function (other) {
        return other;
    },
    equal: function (other) {
        return other === this;
    },
    effectiveMapOver: function (_other: CollectionTypeDescriptor) {
        return NULL_COLLECTION_TYPE_DESCRIPTION;
    },
};

export const ANY_COLLECTION_TYPE_DESCRIPTION: CollectionTypeDescriptor = {
    isCollection: true,
    collectionType: "any",
    rank: -1,
    canMatch: function (other) {
        return NULL_COLLECTION_TYPE_DESCRIPTION !== other;
    },
    canMapOver: function () {
        return false;
    },
    toString: function () {
        return "AnyCollectionType[]";
    },
    append: function () {
        return ANY_COLLECTION_TYPE_DESCRIPTION;
    },
    equal: function (other) {
        return other === this;
    },
    effectiveMapOver: function (_other: CollectionTypeDescriptor) {
        return NULL_COLLECTION_TYPE_DESCRIPTION;
    },
};

export class CollectionTypeDescription implements CollectionTypeDescriptor {
    collectionType: string;
    isCollection: true;
    rank: number;

    constructor(collectionType: string) {
        this.collectionType = collectionType;
        this.isCollection = true;
        this.rank = collectionType.split(":").length;
    }
    append(other: CollectionTypeDescriptor): CollectionTypeDescriptor {
        if (other === NULL_COLLECTION_TYPE_DESCRIPTION) {
            return this;
        }
        if (other === ANY_COLLECTION_TYPE_DESCRIPTION) {
            return other;
        }
        return new CollectionTypeDescription(`${this.collectionType}:${other.collectionType}`);
    }
    canMatch(other: CollectionTypeDescriptor) {
        const otherCollectionType = other.collectionType;
        if (other === NULL_COLLECTION_TYPE_DESCRIPTION) {
            return false;
        }
        if (other === ANY_COLLECTION_TYPE_DESCRIPTION) {
            return true;
        }
        if (otherCollectionType === "paired" && this.collectionType == "paired_or_unpaired") {
            return true;
        }
        if (this.collectionType.endsWith(":paired_or_unpaired")) {
            const asPlainList = this.collectionType.slice(0, -":paired_or_unpaired".length);
            if (otherCollectionType === asPlainList) {
                return true;
            }
            const asPairedList = `${asPlainList}:paired`;
            if (otherCollectionType === asPairedList) {
                return true;
            }
        }
        return otherCollectionType == this.collectionType;
    }
    canMapOver(other: CollectionTypeDescriptor) {
        if (!other.collectionType || other.collectionType === "any") {
            return false;
        }
        if (this.rank <= other.rank) {
            if (other.collectionType == "paired_or_unpaired") {
                // this can be thought of as a subcollection of anything except a pair
                // since it would match a pair exactly
                return !this.collectionType.endsWith("paired");
            }
            if (other.collectionType.endsWith(":paired_or_unpaired")) {
                return !this.collectionType.endsWith(":paired");
            }
            // Cannot map over self...
            return false;
        }
        const requiredSuffix = other.collectionType;
        const directMatch = this._endsWith(this.collectionType, `:${requiredSuffix}`);
        if (directMatch) {
            return true;
        }
        // this really needs to be extended to include anything suffixed with :paired_or_unpaired
        if (requiredSuffix == "paired_or_unpaired") {
            // anything can be mapped over this since it can always act a dataset
            return true;
        } else if (requiredSuffix.endsWith(":paired_or_unpaired")) {
            const higherRanksRequired = requiredSuffix.substring(0, requiredSuffix.lastIndexOf(":"));
            let higherRanks: string;
            if (this.collectionType.endsWith(":paired")) {
                higherRanks = this.collectionType.substring(0, this.collectionType.lastIndexOf(":"));
            } else {
                higherRanks = this.collectionType;
            }
            return this._endsWith(higherRanks, higherRanksRequired);
        }
        return false;
    }
    effectiveMapOver(other: CollectionTypeDescriptor): CollectionTypeDescriptor {
        const thisCollectionType = this.collectionType;
        if (other.collectionType && this.canMapOver(other)) {
            const otherCollectionType = other.collectionType;
            // needs to be extended to include ending in :paired_or_unpaired.
            if (otherCollectionType.endsWith("paired_or_unpaired")) {
                if (otherCollectionType == "paired_or_unpaired") {
                    if (thisCollectionType.endsWith("list")) {
                        // the elements of the inner most list are consumed by the
                        // paired_or_unpaired input.
                        return new CollectionTypeDescription(thisCollectionType);
                    }
                    return new CollectionTypeDescription(
                        thisCollectionType.substring(0, thisCollectionType.lastIndexOf(":")),
                    );
                } else if (thisCollectionType.endsWith(":paired") || thisCollectionType.endsWith(":list")) {
                    // otherCollectionType endswith :paired_or_unpaired
                    let currentCollectionType = thisCollectionType;
                    let currentOther = otherCollectionType;
                    while (currentOther.lastIndexOf(":") !== -1) {
                        currentOther = currentOther.substring(0, currentOther.lastIndexOf(":"));
                        currentCollectionType = currentCollectionType.substring(
                            0,
                            currentCollectionType.lastIndexOf(":"),
                        );
                    }
                    // and strip the last rank off for the remaining currentOther if
                    // the paired_or_unpaired consumed the inner paired collection
                    if (thisCollectionType.endsWith(":paired")) {
                        currentCollectionType = currentCollectionType.substring(
                            0,
                            currentCollectionType.lastIndexOf(":"),
                        );
                    } else {
                        // this was a list so paired_or_unpaired will consume the datasets of the
                        // inner list and we can just stop here.
                    }
                    return new CollectionTypeDescription(currentCollectionType);
                }
            }
            const effectiveCollectionType = thisCollectionType.substring(
                0,
                thisCollectionType.length - otherCollectionType.length - 1,
            );
            return new CollectionTypeDescription(effectiveCollectionType);
        }
        return NULL_COLLECTION_TYPE_DESCRIPTION;
    }
    equal(other: CollectionTypeDescriptor | null) {
        if (!other) {
            return false;
        }
        return other.collectionType == this.collectionType;
    }
    toString() {
        return `CollectionType[${this.collectionType}]`;
    }
    _endsWith(str: string, suffix: string) {
        return str.indexOf(suffix, str.length - suffix.length) !== -1;
    }
}

const collectionTypeRegex =
    /^((list|paired|paired_or_unpaired|record)(:(list|paired|paired_or_unpaired|record))*|sample_sheet|sample_sheet:paired|sample_sheet:record|sample_sheet:paired_or_unpaired)$/;

export function isValidCollectionTypeStr(collectionType: string | undefined) {
    if (collectionType) {
        return collectionTypeRegex.test(collectionType);
    } else {
        return true;
    }
}
