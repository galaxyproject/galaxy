# Best practices when querying the API from UI components

If you need to query the API from a component, there are several ways to do so. This document will help you decide which one to use and provide some best practices when doing so to keep the code clean and maintainable.

## Choose the Right Approach

When querying APIs in Vue components, consider the following approaches and their best practices:

## 1. Prefer Composables over Stores over Direct API Calls

### Composables

-   **What Are Composables?**: please read the official Vue documentation on composables [here](https://vuejs.org/guide/reusability/composables.html).

If there is already a composable that takes care of the logic you need for accessing a particular resource in the API please use it or consider writing a new one. They provide a type-safe interface and a higher level of abstraction than the related Store or the API itself. They might rely on one or more Stores for caching and reactivity.

### Stores

-   **Stores Explained**: Please read the official Vue documentation on State Management [here](https://vuejs.org/guide/scaling-up/state-management.html).

If there is no Composable for the API endpoint you are using, try using a (Pinia) Store instead. Stores are type-safe and provide a reactive interface to the API. They can also be used to cache data, ensuring a single source of truth.

-   **Use Pinia Stores**: If you need to create a new Store, make sure to create a Pinia Store, and not a Vuex Store as Pinia will be the replacement for Vuex. Also, use [Composition API syntax over the Options API](https://vuejs.org/guide/extras/composition-api-faq.html) for increased readability, code organization, type inference, etc.

### Direct API Calls

-   If the type of data you are querying should not be cached, or you just need to update or create new data, you can use the API directly. Make sure to use the **Fetcher** (see below) instead of Axios, as it provides a type-safe interface to the API along with some extra benefits.

## 2. Prefer Fetcher over Axios (when possible)

-   **Use Fetcher with OpenAPI Specs**: If there is an OpenAPI spec for the API endpoint you are using (in other words, there is a FastAPI route defined in Galaxy), always use the Fetcher. It will provide you with a type-safe interface to the API.

**Do**

```typescript
import { fetcher } from "@/api/schema";
const datasetsFetcher = fetcher.path("/api/dataset/{id}").method("get").create();

const { data: dataset } = await datasetsFetcher({ id: "testID" });
```

**Don't**

```js
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

async getDataset(datasetId) {
    const url = `${getAppRoot()}api/datasets/${datasetId}`;
    try {
        const response = await axios.get(url);
        return response.data;
    } catch (e) {
        rethrowSimple(e);
    }
}

const dataset = await getDataset("testID");
```

> **Reason**
>
> The `fetcher` class provides a type-safe interface to the API, and is already configured to use the correct base URL and error handling.

## 3. Where to put your API queries?

The short answer is: **it depends**. There are several factors to consider when deciding where to put your API queries:

### Is the data you are querying related exclusively to a particular component?

If so, you should put the query in the component itself. If not, you should consider putting it in a Composable or a Store.

### Can the data be cached?

If so, you should consider putting the query in a Store. If not, you should consider putting it in a Composable or the component itself.

### Is the query going to be used in more than one place?

If so, you should consider putting it under src/api/<resource>.ts and exporting it from there. This will allow you to reuse the query in multiple places specially if you need to do some extra processing of the data. Also it will help to keep track of what parts of the API are being used and where.

### Should I use the `fetcher` directly or should I write a wrapper function?

-   If you **don't need to do any extra processing** of the data, you can use the `fetcher` directly.
-   If you **need to do some extra processing**, you should consider writing a wrapper function. Extra processing can be anything from transforming the data to adding extra parameters to the query or omitting some of them, handling conditional types in response data, etc.
-   Using a **wrapper function** will help in case we decide to replace the `fetcher` with something else in the future (as we are doing now with _Axios_).
