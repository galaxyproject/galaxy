Translating the Interface
=========================

A quick tutorial on translating the Galaxy UI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Translations in Galaxy are done by simple dictionary lookup of text. Whatever text is written in the interface, the client will look it up in its dictionary, and if it's there, return it. If it's not, it will return the English text that was used to search.

Translations are stored in ``client/src/nls/XX/locale.js`` files where `XX` is the ISO 639 2-letter code for a language. A `locale.js` file looks like this:

.. code-block:: js

    define({
        // ----------------------------------------------------------------------------- masthead

        "Analyze Data": "Analizar Datos",
        "Tools and Current History": "Herramientas e Historial Actual",
        Workflow: "Flujo de Trabajo",

The last three lines contain a mapping of English text to their Spanish equivalents. But before we can add translations here, we need to know what English text is being used in the interface. Generally this is a process of:

- Find untranslated text in the UI
- Find the corresponding text in the codebase
- Ensure that it uses `_l()` localisation statements
- Add the translation for that text to the `locale.js` file.

A quick example.
~~~~~~~~~~~~~~~~

In the user preferences menu I saw the text: "You are logged in as hxr@local.host." I can guess that the email address is templated out, so I'm going to search for "You are logged in as". Running that query I see some results:

.. code-block:: shell

    $ grep -R 'You are logged in as' client/src/
    client/src/mvc/library/library-library-view.js:                        You are logged in as an <strong>administrator</strong> therefore you can manage any library
    client/src/components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryPermissionsWarning.vue:                You are logged in as an <strong>administrator</strong> therefore you can manage any folder on this
    client/src/components/User/UserPreferences.vue:            You are logged in as <strong id="user-preferences-current-email">{{ email }}</strong

There! That's a hit, the last file has the string we're looking for. Let's open that file and discover the next challenge...

Types of Strings and how to translate them
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are a number of ways text gets used in the codebase, especially the new Vue JavaScript framework.

1. Text within an element:

   .. code-block:: html

       <b>Some Text</b>

2. Text within a more complex element:

   .. code-block:: html

       <b><icon library>Some Text</b>

3. Attribute or placeholder text

   .. code-block:: html

       <b-form-input v-model="newLibraryForm.synopsis" placeholder="Synopsis of the library" />

And each of these have different ways of being updated to support translations:

1. Text within an element:

   .. code-block:: diff

       -<b>Some Text</b>
       +<b v-localize>Some Text</b>

2. Text within a more complex element:

   .. code-block:: diff

       -<b><icon library>Some Text</b>
       +<b><icon library>{{ titleSomeText }}</b>

3. Attribute or placeholder text

   .. code-block:: diff

       -<b-form-input v-model="newLibraryForm.synopsis" placeholder="Synopsis of the library" />
       +<b-form-input v-model="newLibraryForm.synopsis" :placeholder="titleSynopsis" />

The first one is the easiest, we can just add the ``v-localize`` tag and we're done, the library knows how to translate it. The second two are a bit more complicated. You'll notice we introduced a new variable in each (``titleSomeText``, ``titleSynopsis``). Because we can't translate the terms directly there, we need to put the translated text into a variable.

For those you'll need to have a quick overview of the structure of a Vue component to localize the correct place to set the variable. The exact structure will not always be identical but it should be similar. At the top is a ``<template>`` section which contains what will be rendered, and at the bottom is a ``<script>`` section which contains some code that's run as part of rendering that UI component.

.. code-block:: html

    <template>
        <span class="position-relative">
            <b><font-awesome-icon icon="upload" class="mr-1" /> Upload Data</b>
        </span>
    </template>

    <script>
    import { VBTooltip } from "bootstrap-vue";
    import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
    import { library } from "@fortawesome/fontawesome-svg-core";

    export default {
        components: { FontAwesomeIcon },
        ...
        data() {
            return {
                status: "",
                percentage: 0,
            };
        },

What you're looking for is the ``data()`` block which returns a dictionary. There we can define our new variable. Here's how our localized component would change:

.. code-block:: diff

     <template>
         <span class="position-relative">
    -        <b><font-awesome-icon icon="upload" class="mr-1" /> Upload Data</b>
    +        <b><font-awesome-icon icon="upload" class="mr-1" /> {{ titleUploadData }}</b>
         </span>
     </template>

     <script>
    +import _l from "utils/localization";
     import { VBTooltip } from "bootstrap-vue";
     import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
     import { library } from "@fortawesome/fontawesome-svg-core";

     export default {
         components: { FontAwesomeIcon },
         ...
         data() {
             return {
                 status: "",
                 percentage: 0,
    +            titleUploadData: _l("Upload Data"),
             };
         },

Which should result in a translated UI!
