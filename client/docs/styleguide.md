# Styleguide

Most of the client's code style is handled by Prettier. Prettier does a good job of keeping an overall consistent code style, however there are some cases it cannot account for.
This document serves as a guide on how to style your code in such cases, with explanations as to why.
Treat it more like a set of recommendations than hard rules.

## Naming

Do not abbreviate. This includes naming variables, functions and modules.

> **Do**
>
> ```js
> function errorMessageTemplate(workflowfName, errorMessage) {
>     return `Failed to run ${workflowfName}. ${errorMessage}`;
> }
> ```
>
> **Don't**
>
> ```js
> function eMsgTmpl(wfName, msg) {
>     return `Failed to run ${wfName}. ${msg}`;
> }
> ```

> **Reason**
>
> While abbreviation may save a few keystrokes now, it will make the code harder to understand, and therefore maintain. Even when you think the abbreviations are obvious within this context, consider people looking at your code in the future might not have the same context you do when writing the code.

## Functions

There are several ways to define functions in JavaScript.

```js
// named function
function myFunction(param) {
    // do stuff
}

// arrow functions
const myFunction = (param) => {
    // do stuff
};

// anonymous functions
const myFunction = function (param) {
    //do stuff
};
```

Only use the first two.
`anonymous functions` have mostly been superseded by `arrow functions`

### When to use the named functions

Use named functions in the top-level module scope and to declare class methods.

> **Reason**
>
> `function` is easy to process and understand at a glance. In module scope, arrow functions offer no benefit over regular functions, and they are not allowed as class methods.

### When to use arrow functions

Use arrow functions when declaring temporary functions within other scopes. This can be within another function, or inside a method that expects a callback function (eg. `array.forEach()`).

> **Reason**
>
> Arrow functions offer benefits about the ambiguity of the `this` keyword within other scopes, as they do not provide their own `this` context.
>
> Binding them to a variable, also makes it clear that this function only exists within said scope, just like any other scoped variable.

### When to use anonymous functions

When possible, use arrow functions instead.

### Examples

> **Do**
>
> ```js
> // in myModules.js
>
> export function myFunction(parameter) {
>     const addOne = (value) => {
>         return value + 1;
>     };
>     // do more stuff...
> }
> ```
>
> **Don't**
>
> ```js
> // in myModules.js
>
> export const myFunction = (parameter) => {
>     const addOne = function (value) {
>         return value + 1;
>     };
>     // do more stuff...
> };
> ```

## HTML Multi-Line Layout

Prettier tries to respect whitespace when formatting your HTML templates, even when it doesn't need to. So for example this code:

```vue
<b-button class="danger-button mb-4" variant="danger" @click="onDangerButtonClick">A very Long Button Text</b-button>
```

Might get turned into:

```vue
<b-button class="danger-button mb-4" variant="danger" @click="onDangerButtonClick">A very Long Button Text</b-button>
```

Notice the strange positioning of the `>` brackets.

In this case the formatting is equivalent to the much more readable:

```vue
<b-button class="danger-button mb-4" variant="danger" @click="onDangerButtonClick">
    A very Long Button Text
</b-button>
```

Prettier does not know if our element has significant whitespace, or not. Check if your element has significant whitespace, and if it does not, reformat the HTML to avoid disjointed brackets.

[Further reading about significant whitespace](https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model/Whitespace)

## Spacing

Prettier doesn't add empty lines to your code, but they can help in making it more readable.

### Javascript

Add an empty line between a block of variable definitions and other code.

> **Do**
>
> ```js
> let a = 5;
> let b = 6;
>
> console.log(a + b);
> ```
>
> **Don't**
>
> ```js
> let a = 5;
> let b = 6;
> console.log(a + b);
> ```

Add space between scopes.

> **Do**
>
> ```js
> function myFunction(parameter) {
>     if (condition) {
>         // do stuff...
>     }
>
>     if (otherCondition) {
>         // do more stuff...
>     }
> }
>
> function otherFunction() {
>     // do other stuff...
> }
> ```
>
> **Don't**
>
> ```js
> function myFunction(parameter) {
>     if (condition) {
>         // do stuff...
>     }
>     if (otherCondition) {
>         // do more stuff...
>     }
> }
> function otherFunction() {
>     // do other stuff...
> }
> ```

Add space between scopes and other code.

> **Do**
>
> ```js
> const myConstant = 5;
>
> if (myConstant === 5) {
>     // do stuff...
> }
>
> console.log("log stuff");
> ```
>
> **Don't**
>
> ```js
> const myConstant = 5;
> if (myConstant === 5) {
>     // do stuff...
> }
> console.log("log stuff");
> ```

### Vue Components

Add spaces between the `script`, `template` and `style` blocks.

> **Do**
>
> ```vue
> <script setup>
> // do stuff...
> </script>
>
> <template>
>     <!--template stuff-->
> </template>
>
> <style lang="scss" scoped>
> // stlye stuff...
> </style>
> ```
>
> **Don't**
>
> ```vue
> <script setup>
> // do stuff...
> </script>
> <template>
>     <!--template stuff-->
> </template>
> <style lang="scss" scoped>
> // stlye stuff...
> </style>
> ```

### Vue Templates

Do not add space between elements connected by conditionals.

> **Do**
>
> ```vue
> <div>
>     <span v-if="conditional">
>         condition met
>     </span>
>     <span v-else>
>         condition not met
>     </span>
> </div>
> ```
>
> **Don't**
>
> ```vue
> <div>
>     <span v-if="conditional">
>         condition met
>     </span>
> 
>     <span v-else>
>         condition not met
>     </span>
> </div>
> ```

Add space between non-connected elements.

> **Do**
>
> ```vue
> <div>
>     <span>
>         First span.
>     </span>
> 
>     <span>
>         Second span.
>     </span>
> </div>
> ```
>
> **Don't**
>
> ```vue
> <div>
>     <span>
>         First span.
>     </span>
>     <span>
>         Second span.
>     </span>
> </div>
> ```

Add space between logical blocks of elements.

> **Do**
>
> ```vue
> <div>
>     <span v-if="conditional">
>         condition 1 met
>     </span>
>     <span v-else>
>         condition 1 not met
>     </span>
> 
>     <span v-if="otherConditional">
>         condition 2 met
>     </span>
>     <span v-else>
>         condition 2 not met
>     </span>
> </div>
> ```
>
> **Don't**
>
> ```vue
> <div>
>     <span v-if="conditional">
>         condition 1 met
>     </span>
>     <span v-else>
>         condition 1 not met
>     </span>
>     <span v-if="otherConditional">
>         condition 2 met
>     </span>
>     <span v-else>
>         condition 2 not met
>     </span>
> </div>
> ```

## Casting

Use explicit boolean casting.

> **Do**
>
> ```js
> const condition = Boolean(value);
> ```
>
> **Don't**
>
> ```js
> const condition = !!value;
> ```

> **Reason**
>
> `!!` is not an intentional casting operator. The casting is a side-effect of the `!` operator. Using explicit casting is easier to understand at a glance.

## Equality

When possible, use strict equality.

> **Do**
>
> ```js
> if (value === 5) {
>     // do stuff...
> }
>
> if (otherValue !== 6) {
>     // do more stuff...
> }
> ```
>
> **Don't**
>
> ```js
> if (value == 5) {
>     // do stuff...
> }
>
> if (otherValue != 6) {
>     // do more stuff...
> }
> ```

> **Reason**
>
> Strict equality simply checks if two values are equal. Loose equality does type conversion under the hood and is a lot more complicated. While in most cases these do the same, due to the added complexity of loose equality, there are some edge cases where loose equality (`==`) can lead to unexpected problems.
>
> For consistency, treat `===` as the default for equality checking.
>
> [Read more on MDN](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Strict_equality)

## Default value assignment

Use `??` to assign default values.

> **Do**
>
> ```js
> const value = parameter ?? 0;
> ```
>
> **Don't**
>
> ```js
> const value = parameter || 0;
> ```

> **Reason**
>
> The `??` operator uses the right hand value, when the left hand one is unassigned (`undefined` or `null`), while `||` does this on all falsely values (eg. `false` or `0`). This can lead to unexpected bugs in edge cases.
>
> [Read more on MDN](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Nullish_coalescing#assigning_a_default_value_to_a_variable)

### Working with unused variables

Unused variables are marked as errors in eslint, however when destructuring objects to remove
certain keys you may be left with a variable you will not use further. You can
name the unused variable `ignoredUnused`. The `no-unused-vars` config setting in `client/.eslintrc`
contains `"varsIgnorePattern": "[iI]gnoreUnused.*"}` to ignore unused variables if they
start with `ignoredUnused` or `IgnoredUnused`.
