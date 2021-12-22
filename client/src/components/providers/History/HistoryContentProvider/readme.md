The history content provider is where the grunt-work of loading, polling and caching
happens. The output of the provider is a list of current data suitable for rendering in the companion Scroller component.

### Design

The API of the provider is a renderless Vue component. Its inputs are the history and the
currently selected filters. Internally, it tracks the user's current scroll position on the scrolling list then combines those 3 values to ultimately expose an object containing all the
currently-visible content for the history along with some other values that are useful
for the scroller to render the visible window of data.

#### Composition
```html static
<HistoryContentProvider
    :parent="history" 
    :params="params" 
    v-slot="{ setScrollPos, loading, scrolling, payload }">

    <!-- other UI elements that care about the current content,
    filters editors, etc -->

    <Scroller 
        :items="payload.contents"
        :top-placeholders="payload.topRows"
        :bottom-placeholders="payload.bottomRows"
        :scroll-to="payload.startKey"
        @scroll="setScrollPos">

        <template v-slot="{ item, index }">
            <!-- single item rendering -->
        </template>

    </Scroller>

</HistoryContentProvider>
```

#### History Content Provider exposed slot props (outputs)
```js
{
    // a function to update the internal scroll position
    setScrollPos: fn,

    // current content window
    payload: {
        contents: [] 
        topRows: 10 
        botttomRows: 100,
        startKey: "123",
    },

    // flags
    loading: true,
    scrolling: false,
}
```

### Implementation

Because actually delivering that data is kind of a complex process (see dependency graph below) and has multiple goals, Vue's rather
simplistic observability system is not by itself be an ideal means to actually deliver the
constantly shifting payload value. Instead, we used RxJS and its more sophisticated, but admittedly
more complex API.

The goal of this section is to explain how the RxJS works inside the history content provider to
deliver the payload from the 3 changing inputs.

I believe it's easiest to follow RxJS streams by simply drawing a map of them. An rxjs operator is a
functional transformation of a source observable emitter into a new observable emitter and therefore
a combined composition of them (often called a stream) is essentially its own dependency tree. All
you have to do is connect the inputs to the outputs.

### RxJS Flowchart

