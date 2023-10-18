# [Help] How to use a tool form

1. Select data **inputs**
2. Set tool **parameters**
3. Click **Run Tool**

:::info
More about this tool...

-   Tool name `**name** description`
-   Tool version `**version**`
-   This tool has **N** required inputs
    -   input1 with datatype format of `**list of datatypes**`
    -   input2 with datatype format of `**list of datatypes**`
-   See the **tool help** `scrolls tool form down to help section`
    :::

-- > _Reference tool wrapper_

```
<tool id="Cut1" name="Cut" version="1.0.2">
    <description>
        columns from a table
    </description>
```

## :question: Help

:::success
Galaxy concepts
:::

### Input Data

-   Inputs are data _files_
-   Inputs are commonly named **[datasets](https://training.galaxyproject.org/training-material/search2?query=dataset)** in Galaxy
-   Inputs on tool forms are chosen from the _currently active_ **[history](https://training.galaxyproject.org/training-material/search2?query=history)**
-   **[Upload](https://training.galaxyproject.org/training-material/search2?query=upload)** or **[copy](https://training.galaxyproject.org/training-material/faqs/galaxy/histories_copy_dataset.html)** datasets into your history to use them

:flashlight: Switch which history is active with `fa-exchange` or view all of your histories with `history-selector-icon`

### Inputs: one or many?

-   Input data can be ...
    -   a single dataset `fa-file`
    -   a set of multiple datasets `fa-files`
    -   a set of multiple datasets in a [dataset collection](https://training.galaxyproject.org/training-material/search2?query=collection) `fa-folder`

### Input format: Datatype

-   Inputs have a file format commonly named a **datatype** in Galaxy
-   Datatypes are metadata that describe what a file contains.
-   Datatypes are similiar to a file extention but are not a part of the file name.
-   When the _expected_ datatype on the form matches an _assigned_ datatype, a dataset becomes available to select on the tool form.

### Learn

-   [Introduction to Galaxy Analyses](https://training.galaxyproject.org/training-material/topics/introduction/)
-   [Collections are folders of similiar files!](https://training.galaxyproject.org/training-material/search2?query=collection)
-   [Upload: Getting Data into Galaxy](https://help.galaxyproject.org/t/getting-data-into-galaxy/10868)
