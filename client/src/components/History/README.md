### History Panel Component Tree
This is not intended to be a complete listing, but a general idea of how the components are intended
to interact with each other.

```html static
<Index :history="history">
    
    <!-- for the right-hand side history we show some
    optional nav elements, can be ommitted for histories
    shown in multi-history view -->
    <slot:nav>
        <HistorySelector />
        <HistoryMenu />
    </slot:nav>


    <!-- if main history selected -->
    <CurrentHistory :history="history">

        <!-- Data providers do the heavy-lifting of mixing params, history, and 
        scroll position to deliver the content for the scroller -->

        <UrlDataProvider>
            <HistoryDetails />
            <HistoryMessages />
            <ContentOperations />
            <Listing>

                <!-- ContentItem is a dynamic component that becomes
                either Dataset or DatasetCollection depending
                on the props passed to it -->

                (<ContentItem />)
                    <Dataset />
                    <!-- or -->
                    <DatasetCollection />

            </Listing>
        </UrlDataProvider>

    </CurrentHistory>


    <!-- When a collection is selected for viewing, send in a 
    breadcrumbs list of collections the user has selected -->

    <CurrentCollection :selected-collections="breadcrumbs">
        <UrlDataProvider>
            <CollectionNav />
            <Details />
            <Listing>

                <!-- Subdataset and Subcollection are similar to the Dataset 
                and DatasetCollection ContentItem components, but mostly 
                read-only since they are part of the collection-->

                (<ContentItem />)
                    <Subdataset />
                    <!-- or -->
                    <Subcollection />

            </Listing>
        </UrlDataProvider>
    </CurrentCollection>

</Index>
```