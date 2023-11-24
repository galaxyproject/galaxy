# Working with unused variables

Unused variables are marked as errors in eslint, however when destructuring objects to remove
certain keys you may be left with a variable you will not use further.
Prefix the unused variable with an underscore: `_unused`.
The `no-unused-vars` config setting in `client/.eslintrc` contains `"varsIgnorePattern": "_.+"}`
to ignore unused variables if they start with `_`.

Example:

```js
const myObject = {
    name: "history",
    count: 5,
    values: ["a", "b", "c"],
};

const { values: _discarded, ...otherObject } = myObject;

console.log(otherObject); // Object { name: "history", count: 5 }
```
