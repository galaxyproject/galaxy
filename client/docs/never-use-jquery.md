Did you know, jQuery is old enough to drive? It's old enough to get a driver's license. jQuery is a
tool that was built to deal with inconsistencies in browsers that NO LONGER EXIST. In a couple
years, jQuery will be voting, drinking, and capable of being tried as an adult.

If you think you need jQuery, you are mistaken. Please seek help from somebody in the wg-ui-ux
workgroup. There is nothing jQuery can provide you that isn't already part of vanilla javascript or
a standard well-tested 3rd party modern npm module.

But that's not even the main problem. jQuery injects global initializations into every page on the
site whether you want it or not. jQuery leverages an outdated initialization paradigm which is
hugely problematic when it comes to unit testing and module building.

One of our most important goals in redesigning Galaxy is the complete elimination of this library
from our source, along with all its invasive plugins.

### References

-   [You Don't Need jQuery](https://github.com/nefe/You-Dont-Need-jQuery)
-   [document.querySelector](https://developer.mozilla.org/en-US/docs/Web/API/Document/querySelector)
