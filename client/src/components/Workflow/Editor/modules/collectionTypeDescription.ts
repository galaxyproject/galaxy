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
        if (other === NULL_COLLECTION_TYPE_DESCRIPTION) {
            return false;
        }
        if (other === ANY_COLLECTION_TYPE_DESCRIPTION) {
            return true;
        }
        return other.collectionType == this.collectionType;
    }
    canMapOver(other: CollectionTypeDescriptor) {
        if (!other.collectionType || other.collectionType === "any") {
            return false;
        }
        if (this.rank <= other.rank) {
            // Cannot map over self...
            return false;
        }
        const requiredSuffix = other.collectionType;
        return this._endsWith(this.collectionType, requiredSuffix);
    }
    effectiveMapOver(other: CollectionTypeDescriptor): CollectionTypeDescriptor {
        if (other.collectionType && this.canMapOver(other)) {
            const otherCollectionType = other.collectionType;
            const effectiveCollectionType = this.collectionType.substring(
                0,
                this.collectionType.length - otherCollectionType.length - 1
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

const collectionTypeRegex = /^(list|paired)(:(list|paired))*$/;

export function isValidCollectionTypeStr(collectionType: string | undefined) {
    if (collectionType) {
        return collectionTypeRegex.test(collectionType);
    } else {
        return true;
    }
}
