Without a doubt. The most problematic part of the old client is the way every important piece of
information was hung on a global variable whose initialization is completely unregulated.

### Don't directly reference window.Galaxy in Vue components

Components take props. Please pass in any values you might need from window.Galaxy as props and
avoid referencing global Galaxy inside your components. I've even created basic providers which give
you access to the Galaxy.config, current user, and current user histories. Please use them to
retrieve your values, and bypass importing Galaxy altogether.

#### Sometimes you still need to update Vue from backbone as the legacy environment changes
There are definitely use-cases where the Backbone models update over time and we need to update some
value inside Vue. Instead of importing backbone models directly into Vue components, try building a
backbone event listener that updates some relevant Vuex store.

* [Keeping Vuex in Sync with
  Galaxy](https://github.com/galaxyproject/galaxy/blob/dev/client/src/store/syncVuexToGalaxy.js)

These issues should disappear over time as the all of the old client is rebuilt in the new
ecosystem.


## Mount Functions

In what most people think of as a "standard" Vue application there would be only one place that Vue
is mounted to the HTML environment, and that would be in a main.j or an app.js. Most modern
single-page applications only have one starting point like that.

However, we are incrementally replacing old Backbone views, so in its current state, Galaxy may have
several mounting functions for various components depending on where that component is intended to
fit into the existing Backbone layouts.


### Using the standard mount to pass in Galaxy variables as props

A standard mount function has been provided in src/utils. This mount function accepts a component
definition, and then allows you to start up your Vue component with our standard load-out of plugins
including localization, Vuex, and a couple other utilities. This is the preferred way to mount your
component inside the old Backbone layout until the application is fully converted.

```js static
// src/mvc/OldBackboneView.js

import { getGalaxyInstance } from "app";
import MyComponent from "components/MyComponent";
import { mountVueComponent } from "utils/mountVueComponent";

const OldBackboneView = {

    someInitMethodYouMake() {
        const Galaxy = getGalaxyInstance();
        const mounter = mountVueComponent(MyComponent);

        // pass in required props
        const props = { 

            // Something peeled off the global galaxy
            somePropVal: Galaxy.someDealie, 

            // ...or the current history
            name: Galaxy.currentHistory.name,

            // or maybe from the backbone model for this view
            shoeSize: this.model.shoeSize
        };

        // VM is a Vue instance.
        // this.$el is some jquery selection, first item is the actual DOM object
        const container = this.$el[0];
        const vm = mounter(props, container);
    }
}
```
