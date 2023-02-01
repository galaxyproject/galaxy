# Composables

Composables are way of splitting up your code into distinct, reusable chunks.
They can replace providers, mixins and more. Any code you can put into a component, can also be written as a composable.
Using them effectively can make your code more reusable, decoupled, and easier to follow.

**More about Composables:**

-   [Composables Overview](https://vuejs.org/guide/reusability/composables.html)
-   [Composition API](https://vuejs.org/api/composition-api-setup.html)
-   [\<script setup\>](https://vuejs.org/api/sfc-script-setup.html)

## Using Composables in the Composition API

Example: accessing the current user from the store

```vue
<script setup>
import { useCurrentUser } from "composables/user";

const { currentUser } = useCurrentUser();
</script>
```

You can now access the current user with `currentUser.value`.

## Using Composables in the Options API

Composables are not limited to the composition api. This is the same example from above, using the options api.

```vue
<script>
import { useCurrentUser } from "composables/user";

export default {
    setup() {
        const { currentUser } = useCurrentUser();
        return { currentUser };
    },
};
</script>
```

You can now access the current user with `this.currentUser` from anywhere within the component.

## Testing Components with Composable Stores

When writing a test which includes a component that has a composable store (like useCurrentUser),
there are two ways to test it.

### Mocking the store

You can provide the store in the mount function as follows:

```js
const wrapper = shallowMount(TestedComponent,
    localVue,
    provide: { store },
});
```

`store` must be a Vuex store.
The `mockModule` helper can help creating a store for the required modules:

```js
const store = new Vuex.Store({
    modules: {
        user: mockModule(userStore),
    },
});
```

### Mocking the composable

The second option is to mock the composable:

```js
import { useCurrentUser } from "composables/user";

jest.mock("composables/user");
useCurrentUser.mockReturnValue({
    currentUser: {},
});
```

While simpler in this example, you may need to manually mock more return values and composables than the other method, depending on the composables the component is using.

## Using Composables for more than Stores

Composables can be of great use to extract any reactive code from your components. For an example of this, take a look at [useFilterObjectArray](https://github.com/galaxyproject/galaxy/blob/dev/client/src/composables/utils/filter.js).

Usage:

```vue
<script setup>
import { useFilterObjectArray } from "composables/utils/filter";

const filteredArray = useFilterObjectArray(someReactiveArray, searchValue, ["name", "description"]);
</script>
```

It's a simple filtering function, but fully reactive.
Whenever any of the inputs changes, the return value is re-computed, without having to call the function again.
