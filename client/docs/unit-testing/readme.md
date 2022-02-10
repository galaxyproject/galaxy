
[Galaxy uses Jest](https://jestjs.io/) for its client-side unit testing
framework.

For testing Vue components, we use the [Vue testing
utils](https://vue-test-utils.vuejs.org/) to mount individual components in a
test bed and check them for rendered features.  Please use jest-based mocking
for isolating test functionality.


### Specific test scenarios & examples

* [Mocking an imported
dependency](https://github.com/galaxyproject/galaxy/blob/dev/client/src/components/Tags/tagService.test.js)
* [Testing async
operations](https://github.com/galaxyproject/galaxy/blob/dev/client/src/components/Tags/tagService.test.js)
* [Testing a Vue component for expected rendering
output](https://github.com/galaxyproject/galaxy/blob/dev/client/src/components/Tags/StatelessTags.test.js)
* [Firing an event against a shallow mounted vue
component](https://github.com/galaxyproject/galaxy/blob/dev/client/src/components/Tags/StatelessTags.test.js)
