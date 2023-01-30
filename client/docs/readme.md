### A component is really just a fancy function

I'm not talking about how webpack turns it into a rendering function. That's obvious.

I mean conceptually, props come in (like arguments) and events go out (like the return statements).
A component is a fancy kind of function that can keep emitting results and accept changing inputs
over time. In truth it more closely resembles an Observable, but an observable is ALSO a slightly
fancier kind of function.

If you just think of a component as thing that takes input props and emits output events you're well
on your way to using them well.

The worst components are ones that might as well just be a big single page script. That's zero
percent better than the spaghetti we're working so hard to replace. That's just repackaging all the
problems of the old imperative class-based legacy code.

### Get comfortable with events, limit your dependence on Vuex

New vue programmers are ok at handing props to components, but they rarely use events effectively
(at first). As a result they end up using a lot of global state, a million little data props and
relying on imperfect globalized tools like Vuex or other imported dependencies for every little
variable.

Vuex definitely has its uses, but not as many as you might expect given the way it is
overly-emphasized in common tutorials. It's easy to walk away from an "Intro to Vue" video with the
idea that all data must live in Vuex all the time. That's a really undesirable situation.

Although vuex is a well-organized (many would say over-organized) state machine, it is important
to remember that it is still a kind of global injection and deserves to be considered as such.

-   [Should I Store This Data in
    Vuex](https://markus.oberlehner.net/blog/should-i-store-this-data-in-vuex/)
-   [Vuex getters are great, but don’t overuse
    them](https://codeburst.io/vuex-getters-are-great-but-dont-overuse-them-9c946689b414)

Data persistence should be something that happens near the top of your component tree, not down in
the guts.

Your first thought with a component should be: "How can I offload the handling of the results of
this component to my caller?" The answer is usually going to be events. A component that simply
accepts props and emits events can be re-used in more contexts than one that relies on an external
global state to operate.

#### Read up on .sync and v-model

They're just fancy shorthands for a prop / event handler combination. They are fundamentally no
different from props and events, but the syntax is important to understand.

### Think carefully about what should really be in "data".

Most of good component design boils down to answering the following question: What do I want to put
in data, computed, and props?

Data is the place where temp data goes that is not sensible to persist in Vuex or other
application-wide global state, usually because its use is very specific to the operation of this
particular component. There really should only be a few variables in data.

#### Break down your own internal dependencies

Most components only need one or two variables in data. If you have a large amount of data
variables, it's worth taking a little time to stop and build a mini-dependency tree for yourself.
You will probably find that almost everything can be written in terms of computed transformations on
a small number of data and properties.

Defining your values using computes will lead to a lot less "oh I forgot to update that
variable"-style bugs.

If you have more than a few data variables you probably (a) aren't leveraging computeds and
properties, or (b) are trying to implement too many features for just one component. It is important
separate your concerns in components just like you do in any other kind of programming.
