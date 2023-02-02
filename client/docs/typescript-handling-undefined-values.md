# Handling Possibly undefined Values in Typescript

You may notice some more typescript errors than the usual, even compared to strict typescript.
This is due to the rule `noUncheckedIndexedAccess` being activated in this project.

Here's an example of what this rule enforces:

`noUncheckedIndexedAccess` disabled

```ts
type NumberDictionary = {
    [key: string]: number;
};

const object: NumberDictionary = {
    keyA: 1,
};

// type of a is number, but it is clearly undefined here
const a = object.keyB;
```

`noUncheckedIndexedAccess` enabled

```ts
type NumberDictionary = {
    [key: string]: number;
};

const object: NumberDictionary = {
    keyA: 1,
};

// type of a is number | undefined, improving type safety
const a = object.keyB;
```

`noUncheckedIndexAccess` causes typescript to evaluate types as possibly undefined in
any scenario where they may be undefined. E.g. when accessing a key of an object with unknown keys,
or a value of an array with unknown length.

This leads to extra type safety during development, but needs some extra care to handle.

Here are some more realistic scenarios and how to handle them.

---

## Unspecific Types

Sometimes this error can be resolved, by simply being stricter about your types. The two main use-cases for this are `tuples` and `readonly objects`. These can also be defined as `arrays` and `records`, however, unlike `tuples` and `readonly objects`, these types have no guarantee that a value exists behind a specific index, which is where the typescript error message comes from.

### Readonly Objects

```ts
const operatorForAlias: Record<string, string> = {
    lt: "<",
    le: "<=",
    ge: ">=",
    gt: ">",
    eq: ":",
};

export function getOperatorForAlias(alias: string): string {
    return operatorForAlias[alias];
}
```

The keys and values of constant object never change. Typescript does not know this, and throws a possible undefined error in the function. This can be solved with more specific types:

```ts
const operatorForAlias = {
    lt: "<",
    le: "<=",
    ge: ">=",
    gt: ">",
    eq: ":",
} as const;

type OperatorForAlias = typeof operatorForAlias;
type Alias = keyof OperatorForAlias;
type Operator = OperatorForAlias[Alias];

export function getOperatorForAlias(alias: Alias): Operator {
    return operatorForAlias[alias];
}
```

`as const` tells typescript the values will never change. The other types restrict the possible inputs and outputs of the function to the objects keys and values respectively, giving us much more detailed type hints, and resolving the error.

To ensure future code changes keep the object as a flat key-value string pair, we can further add `satisfies Record<string, string>` to it, as follows:

```ts
const operatorForAlias = {
    lt: "<",
    le: "<=",
    ge: ">=",
    gt: ">",
    eq: ":",
} as const satisfies Record<string, string>;
```

### Tuples

Consider an array of arrays as follows:

```ts
const validAliases = [
    [">", "_gt"],
    ["<", "_lt"],
];

for (const [alias, substitute] of validAliases) {
    // ...
}
```

The types of `alias` and `substitute` will be `string | undefined`. This is because typescript resolved the type of `validAliases` to `string[][]`: an array of string arrays. The length of the inner string array is unknown here. It could contain 0, 2, or 20 elements, as far as typescript knows, so this type is correct. We however know, that the inner array will always be exactly two strings long.

This is known as a tuple. `[">", "_gt"]` can be restricted to a tuple by setting it's type to `[string, string]`: An array with exactly two elements, the first of type string, the second one also of type string. Tuples do not need to be two elements long, and do not need the same type on every index. E.g a tuple of `[string, string, number]` is perfectly valid.

To make the types of `alias` and `substitute` resolve to `string`, we can change the code as follows:

```ts
const defaultValidAliases: Array<[string, string]> = [
    [">", "_gt"],
    ["<", "_lt"],
];
```

This also restricts what elements can be inserted into this array, further improving type safety.

---

## Potential Errors

Typescript also catches potential errors, which have not been thrown / asserted. These are valid potential error sources, which can not be worked around as in the examples above. Properly asserting them, gives us much more helpful error messages, to track down the source of an issue.

```ts
const outputStep = this.stepStore.getStep(connection.output.stepId);
let terminalSource = outputStep.outputs.find((output) => output.name === connection.output.name);
```

This code will compile with errors, because `outputStep` is potentially undefined. While we may know that this state is not possible, a future error or mistake may still make it possible and properly asserting can be helpful. Here I'm using the new `assertDefined` utility.

```ts
const outputStep = this.stepStore.getStep(connection.output.stepId);
assertDefined(outputStep, `No such step with id ${connection.output.stepId}`);

let terminalSource = outputStep.outputs.find((output) => output.name === connection.output.name);
```

The code will now compile fine.

---

## Defaulting and Optional Chaining

Setting sensible default values, or using optional chaining can also be a way of dealing with possible undefined values in some situations.

Example

```ts
// if otherVar is undefined or null, myVar will be set to 4
const myVar = otherVar ?? 4;

// someFunction will only be called if someObject is not undefined or null
someObject?.someFunction();

// combining both concepts
const myOtherVar = someObject?.getValue() ?? "default";
```

---

## Incorrect Warning

Typescript isn't always right when it comes to these warnings. Sometimes the surrounding code makes it obvious that an undefined value is not possible here. For example:

(This code is modified for this example)

```ts
if (row.length > 0) {
    // Try to split by comma first
    let rowDataSplit = row[0].split(","); // possible undefined error
    if (rowDataSplit.length === num_columns) {
        return rowDataSplit;
    }
    // Try to split by tab
    rowDataSplit = row[0].split("\t"); // possible undefined error
    if (rowDataSplit.length === num_columns) {
        return rowDataSplit;
    }
}
```

Solution 1: Reordering code. To tell typescript that we are sure this value exists, we can simply reorder the code.
This is the preferable solution, as it leads to cleaner code.

```ts
const firstElement = row[0];

if (firstElement) {
    // Try to split by comma first
    let rowDataSplit = firstElement.split(",");
    if (rowDataSplit.length === num_columns) {
        return rowDataSplit;
    }
    // Try to split by tab
    rowDataSplit = firstElement.split("\t");
    if (rowDataSplit.length === num_columns) {
        return rowDataSplit;
    }
}
```

Solution 2: Tell typescript you know better. We can override typescripts assumption using `!`. **Warning:** Only use this if the immediately surrounding code makes it obvious this value exists!

```ts
if (row.length > 0) {
    // Try to split by comma first
    let rowDataSplit = row[0]!.split(",");
    if (rowDataSplit.length === num_columns) {
        return rowDataSplit;
    }
    // Try to split by tab
    rowDataSplit = row[0]!.split("\t");
    if (rowDataSplit.length === num_columns) {
        return rowDataSplit;
    }
}
```

Notice the `!`, behind the element which typescript thought may be undefined.

Sometimes the first solution is not possible, like when we are checking for a specific length. This was the case in the code this example was inspired by. In this case, we must use the second solution:

```ts
[...]
    } else if (row.length === 1) {
        // Try to split by comma first
        let rowDataSplit = row[0]!.split(",");
        if (rowDataSplit.length === num_columns) {
            return rowDataSplit;
        }
        // Try to split by tab
        rowDataSplit = row[0]!.split("\t");
        if (rowDataSplit.length === num_columns) {
            return rowDataSplit;
        }
[...]
```
