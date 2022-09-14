We are using components in two very distinct ways. The first, "normal", kind of component will
probably look familiar to anybody whis is already passingly familiar with Vue. Here the relevant
information comes in as properties, any internal variables get defined in "data", changes go out as
events.

### Composition Example

```html static
<!-- Use of a renderless component with a display component -->
<DoodadProvider v-slot="{ doodad, saveDoodad }">
    <DoodadEditor :doodad="doodad" @update:doodad="saveDoodad" />
</DoodadProvider>
```

In this example, we've created a component whose job is to deal with loading and updating the doodad
object. Notice that there is no markup inside the DoodadProvider other than the explicit renderless
component we previously made, but you are free to putput whatever you want in there, accessing the
doodad and saveDoddad properties as desired, as well as any other local data with the only
restriction that Vue needs a single root element in which to render.


## The Renderer

```html static
<!-- DoodadEditor.vue, a simple "rendering" component -->

<template>
    <AutoComplete
        :options="options"
        :value="doodad.category"  
        @select="saveCategory"
    />
</template>

<script>

export default {
    props: { 
        doodad: { type: Object, required: true },
        options: { type: Array, required: true },
    },
    methods: {
        saveCategory(newCategory) {
            this.$emit('update:doodad', { ...this.doodad, category: newCategory });
        }
    }
}

</script>
```

This component accepts a mandatory input object (doodad), lets the user play with a category prop,
then emits a fresh object after it's done. So what, what's the big deal? The important part to walk
away from this dumb example is the things that are NOT in this sample component. 

This component doesn't save the data. This component doesn't make ajax calls, and this component
doesn't mutate its props. What it does do is to allow the user to edit some object named "doodad"
and emits a new fresh version of that doodad when it's done. (Note also that we are using the
update:propname event syntax whenever possible [to facilitate .sync
binds](https://vuejs.org/v2/guide/components-custom-events.html#sync-Modifier)).

Whatever happens to that new object is somebody else's job. As soon as you tie the data management
to the rendering, the re-usability of your components craters.


## The Provider

As the opposite of the rendering component, a provider or renderless component, is pure logic. It
should not know or care what your renderer is going to do with the data it provides. It is simply a
fancy way of configuring some data manipulation methods. This is one of the many ways of reusing
functionality available in Vue. Some others are [Mixins](https://vuejs.org/v2/guide/mixins.html),
[Provide/Inject](https://v3.vuejs.org/guide/component-provide-inject.html) and (in Vue3) [the
composition API](https://v3.vuejs.org/guide/composition-api-introduction.html).


```js static
// DoodadProvider.js

import { loadDoodad, saveDoodad } from "./someAjaxQueryModule";

export default {
    data() {
        return {
            loaded: false,
            doodad: null
        }
    },
    methods: {
        async saveDoodad(newVal) {
            this.loaded = false;
            const newVal = await saveDoodad(newVal);
            this.doodad = newVal;
            this.loaded = true;
        },
        async loadDoodad(newVal) {
            this.loaded = false;
            const newVal = await loadDoodad(newVal);
            this.loaded = true;
            return newVal;
        }
    },
    async created() {
        this.doodad = await loadDoodad();
    },
    render() {
        return return this.$scopedSlots.default({
            loaded: this.loaded,
            doodad: this.doodad,
            saveDoodad: this.saveDoodad
        });
    }
}
```

Here is an example of a simple possible renderless provider. The important part about this is the
render() function which simply renders [one big default
slot](https://vuejs.org/v2/guide/components-slots.html) and binds some of its own properties to that
slot for use by downstream components.

## Unit Testing a renderless component

Testing of a component like our editor is pretty straightforward and follows the standard Vue
guidelines. If you did a clean-enough job you won't even need to mock anything since all your data
dependencies should be delivered via props.

But it's not so obvious how to unit-test a renderless provider. What do you check for? There's no
mandatory markup, just one big empty slot.

```js static
// Testing a renderless component

import { shallowMount } from "@vue/test-utils";
import { getLocalVue, waitForLifecyleEvent } from "jest/helpers";
import DoodadProvider from "./DoodadProvider";

describe("A renderless component", () => {
    const localVue = getLocalVue();
    let wrapper;
    let slotProps;

    beforeEach(async () => {
        wrapper = shallowMount(DoodadProvider, {
            localVue,
            // The mount fn allows you to hook into a slot for this very reason
            scopedSlots: {
                default(props) {
                    slotProps = props;
                },
            },
        });

        // waits for "updated" Vue lifecycle hook to fire on the renderless 
        // component. This is often good enough for waiting for 
        // an initial ajax load to finish, for example
        await waitForLifecyleEvent(wrapper.vm, "updated");
    })

    test("someProp", () => {
        const { someProp } = slotProps;
        expect(someProp).toExist();
        // ...more tests
    })
})
```