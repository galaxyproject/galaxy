# Beta History Panel Component Tree
This is not intended to be a complete listing, but a general idea of how the components are intended
to interact with each other.

```html
<CurrentHistoryPanel>
    <HistoryPanel :history="history">
        
        <!-- for the right-hand side history we show some
        optional nav elements, can be ommitted for histories
        shown in multi-history view -->
        <slot:nav>
            <HistorySelector />
            <HistoryMenu />
        </slot:nav>


        <!-- if main history selected -->
        <History :history="history">

            <!-- HCP does the heavy-lifting of mixing params, history, and 
            scroll position to deliver the content for the scroller -->

            <HistoryContentProvider :parent="history">
                <HistoryDetails />
                <HistoryMessages />
                <ContentOperations />
                <Scroller>

                    <!-- HistoryContentItem is a dynamic component that becomes 
                    either Dataset or DatasetCollection depending
                    on the props passed to it -->

                    (<HistoryContentItem />)
                        <Dataset />
                        <!-- or -->
                        <DatasetCollection />

                </Scroller>
            </HistoryContentProvider>

        </History>


        <!-- When a collection is selected for viewing, send in a 
        breadcrumbs list of collections the user has selected -->

        <CurrentCollection :selected-collections="breadcrumbs">
            <CollectionContentProvider :parent="selectedCollection">
                <CollectionNav />
                <Details />
                <Scroller>

                    <!-- Subdataset and Subcollection are similar to the Dataset 
                    and DatasetCollection ContentItem components, but mostly 
                    read-only since they are part of the collection-->

                    (<CollectionContentItem />)
                        <Subdataset />
                        <!-- or -->
                        <Subcollection />

                </Scroller>
            </CollectionContentProvider>
        </CurrentCollection>

    </HistoryPanel>
</CurrentHistoryPanel>
```

# General Strategies
These strategies are not intended to be mandates. Every programming problem is different, but this
is an explanation for some of the distinctions which were made during the rewrite of the history
panel. Please understand these strategies at least well-enough to determine whether or not they pertain to your particular problem.
## Providers vs. Renderers

We are using components in two very distinct ways. The first, "normal", kind of component will
probably look familiar to anybody whis is already passingly familiar with Vue. Here the relevant
information comes in as properties, any internal variables get defined in "data", changes go out as events.


```html
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
and emits a new fresh version of that doodad when it's done. (Note also that we are using the update:propname event syntax whenever possible [to facilitate .sync binds](https://vuejs.org/v2/guide/components-custom-events.html#sync-Modifier)).

Whatever happens to that new object is somebody else's job. As soon as you tie the data management
to the rendering, the re-usability of your components craters.

## Providers / Renderless components.
```html
<!-- Use of a renderless component with a display component -->
<DoodadProvider v-slot="{ doodad, saveDoodad }">
    <DoodadEditor :doodad="doodad" @update:doodad="saveDoodad" />
</DoodadProvider>
```

In this example, we've created a component whose job is to deal with loading and updating the
doodad object (which our previous component was created to edit). Notice that there is no
markup inside the DoodadProvider other than the explicit renderless component we previously made,
but you are free to putput whatever you want in there, accessing the doodad and saveDoddad
properties as desired, as well as any other local data with the only restriction that Vue needs a
single root element in which to render.

As the opposite of the rendering component, a provider or renderless component, is pure
functionality. It should not know or care what your renderer is going to do with the data it
provides. It is simply a fancy way of configuring some data manipulation methods. This is one of the
many ways of reusing functionality available in Vue. Some others are 
[Mixins](https://vuejs.org/v2/guide/mixins.html), 
[Provide/Inject](https://v3.vuejs.org/guide/component-provide-inject.html) and (in Vue3) 
[the composition API](https://v3.vuejs.org/guide/composition-api-introduction.html).

```js
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
Here is an example of the dumbest possible renderless provider. The important part about this is the
render() function which simply renders [one big default slot](https://vuejs.org/v2/guide/components-slots.html) and binds some of its own properties to that
slot for use by downstream components.

## Unit-Testing a Renderless Component

Testing of a component like our editor is pretty straightforward and follows the standard Vue
guidelines. If you did a clean-enough job you won't even need to mock anything since all your data
dependencies should be delivered via props.

But it's not so obvious how to unit-test a renderless provider. What do you check for? There's no
mandatory markup, just one big empty slot.

```js
// Unit testing a renderless provider

import { shallowMount } from "@vue/test-utils";
import { getLocalVue, waitForLifecyleEvent } from "jest/helpers";

// test me
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

# Notable Rendering Components

## ContentItem Components
The ContentItem sub-module controls how individual items on  he history list are displayed and
manipulated. It is likely that most of the day-to-day bug-fixes and feature changes will happen in
here, so it is important to be diligent in keeping the separation of concerns (provider/renderer) intact.

### Dataset
### DatasetCollection
### SubDataset
### SubCollection


# Important Providers

## History Content Provider

## Collection Content Provider

# The Caching Layer
### PouchDB
## Known limitations of PouchDB



# Parting Shots, er... Thoughts.

## Don't directly reference window.Galaxy in Vue components
You've got components. Components take props. Please pass in any values you might need from
window.Galaxy as props and avoid referencing global Galaxy inside your components. I've even created
basic providers which give you access to the Galaxy.config, current user, and current user
histories. Please use them to retrieve your values, and bypass importing Galaxy altogether.

There are use-cases where the Backbone models update over time and we need to update some value inside
Vue. Let me help you solve those problems instead of importing backbone models into Vue components.
Usually the answer is a backbone event listener that updates some relevant Vuex store.
## Don't use jQuery in Vue components
Did you know, jQuery is old enough to drive? It's old enough to get a driver's license. jQuery is a
tool that was built to deal with inconsistencies in browsers that NO LONGER EXIST. In
a couple years, jQuery will be voting, drinking, and capable of being tried as an adult. 

If jQuery were a person, I'd be firing it.

If you think you need jQuery, first of all, you are wrong, but secondly, seek help from
me or somebody else in the wg-ui-ux workgroup. I guarantee you there is nothing jQuery can provide
you that isn't already part of vanilla javascript or a standard well-tested 3rd party modern
javascript npm module.

The first step to curing yourself of jQuery is admitting you have a jQuery problem.

# Adapters for existing code
Build your legacy adapters so we can just delete them later when they are no longer required. I have
a special bottle of whiskey I am saving for that glorious day. Here are a few of the adapters I have
had to make for the new Vue history components to work with the old Backbone model catastrophe.

### Sync Vue Store to Galaxy
### HistoryPanelProxy.js


# Debugging Techniques for RxJS operators and observables