## Understand that a component is really just a fancy function

I'm not talking about how webpack turns it into a rendering function. That's obvious.

I mean conceptually, props come in (like arguments) and events go out (like the return statements).
A component is a fancy kind of function that can keep emitting results and accept changing inputs
over time. In truth it more closely resembles an Observable, but an observable is ALSO a slightly
fancier kind of function. 

If you just think of a component as thing that takes inputs and emits outputs you're well on your
way to using them properly.

The worst components are ones that might as well just be a big single script that runs. That's zero
percent better than the spaghetti we're working so hard to replace. That's just repackaging all the
problems of the old imperative class-based legacy code.


## Javascript is a pretty functional language. Classes exist but they aren't as important as you may be used to.

You may come from a class-based programming background and think that your first step should be to
make a class hierchy that does the thing you want. It doesn't help that Vue superficially looks like
a class definition, (even though what you're really doing is configuring an Observable tree). 

But javascript is largely a functional language. Its class support is limited and less useful, and
unless we switch to Typescript, we don't even have interfaces or typing, arguably the most useful
parts of a class-based language. 

In general, you will get more mileage out of javascript by embracing functional programming
approaches because that is what Javascript is good at.


## Get comfortable with events, limit your dependence on Vuex

New vue programmers are ok at handing props to components, but they rarely use events effectively
(at first). As a result they end up using a lot of global state, a million little data props and
relying on imperfect globalized tools like Vuex or other imported dependencies for every little
variable.

Vuex has its uses, but not as many as you might think. Data persistence should be something that
happens near the top of your component tree, not down in the guts. 

Your first thought with a component should be: "How can I offload the handling of the results of
this component to my caller?" The answer is usually going to be events. A component that simply
accepts props and emits events can be re-used in more contexts than one that relies on an external
global state to operate.

### Read up on .sync and v-model

They're just fancy shorthands for a prop / event handler combination. They are fundamentally no
different from props and events, but the syntax is important to understand.



## Think carefully about what should really be in "data".

Most of good component design boils down to answering the following question: What do I want to put
in data, computed, and props?

Data is the place where temp data goes that is not sensible to persist in Vuex or other
application-wide global state, usually because its use is very specific to the operation of this
particular component. There really should only be a few variables in data.

### Break down your own internal dependencies

Most components only need one or two variables in data. If you take the time to analyze your own
internal dependency tree, you will probably find that almost everything can be written in terms of
computed transformations on a small number of data and propertie

If you have more than a few variables you (a) aren't leveraging computeds and properties, or (b) are
trying to implement too many features for just one component. It is important separate your concerns
in components just like you do in any other kind of programming.



## Have a plan

Create a design plan and an abstraction for the way the guts of your component work. Think about the
way data passes from parent components to children and back again. Break your component into
sub-components just like you would break a class into sub-methods, the same exact principles apply.

Don't just dump a pile of spaghetti into a component, that is no better than the legacy code we are
replacing.