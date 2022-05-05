### History Panel Component Tree
This is not intended to be a complete listing, but a general idea of how the components are intended
to interact with each other.

```html static
<Index :history="history">

    <!-- if main history selected -->
    <CurrentHistory :history="history">

        <!-- Data providers do the heavy-lifting of mixing params, history, and 
        scroll position to deliver the content for the scroller -->
        <StoreProvider>
            <HistoryNavigation />
            <HistoryDetails />
            <HistoryMessages />
            <HistoryOperations />

            <!-- Uses a virtual scroller plugin to render all ContentItems and throttles the scrolling pace by limiting
            the frequency and magnitude of offset changes. -->
            <Listing>

                <!-- The ContentItem renders a row in the list, showing the title, some attributes,
                and basic operation buttons such as display and edit for either a dataset or a collection.
                This component needs to be very efficient since it is re-rendered by the virtual scroller plugin. -->
                (<ContentItem />)

                    <!-- Is shown for datasets upon expansion, can be inefficent in comparison to the ContentItem component. -->
                    <DatasetDetails />
            </Listing>
        </StoreProvider>
    </CurrentHistory>

    <!-- When a collection is selected for viewing, send in a 
    breadcrumbs list of collections the user has selected -->
    <CurrentCollection :selected-collections="breadcrumbs">
        <StoreProvider>
            <CollectionNavigation />
            <CollectionDetails />
            <CollectionOperations />

            <!-- As above, the same virtual scroller and ContentItem component is being used to render the elements. -->
            <Listing>
                (<ContentItem />)
                    <DatasetDetails />
            </Listing>
        </StoreProvider>
    </CurrentCollection>
</Index>
```