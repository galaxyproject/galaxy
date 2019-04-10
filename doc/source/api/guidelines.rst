API Design Guidelines
=====================

The following section outlines guidelines related to extending and/or modifying
the Galaxy API. The Galaxy API has grown in an ad-hoc fashion over time by
many contributors and so clients SHOULD NOT expect the API will conform to
these guidelines - but developers contributing to the Galaxy API SHOULD follow
these guidelines.

    - API functionality should include docstring documentation for consumption
      at docs.galaxyproject.org.
    - Developers should familiarize themselves with the HTTP status code definitions
      http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html. The API responses
      should properly set the status code according to the result - in particular
      2XX responses should be used for successful requests, 4XX for various
      kinds of client errors, and 5XX for the errors on the server side.
    - If there is an error processing some part of request (one item in a list
      for instance), the status code should be set to reflect the error and the
      partial result may or may not be returned depending on the controller -
      this behavior should be documented.
    - API methods should throw a finite number of exceptions 
      (defined in :mod:`galaxy.exceptions`) and these should subclass 
      `MessageException` and not paste/wsgi HTTP exceptions. When possible, 
      the framework itself should be responsible catching these exceptions, 
      setting the status code, and building an error response.
    - Error responses should not consist of plain text strings - they should be
      dictionaries describing the error and containing the following::

          {
            "status_code": 400,
            "err_code": 400007,
            "err_msg": "Request contained invalid parameter, action could not be completed.",
            "type": "error",
            "extra_error_info": "Extra information."
          }

      Various error conditions (once a format has been chosen and framework to
      enforce it in place) should be spelled out in this document.
    - Backward compatibility is important and should be maintained when possible.
      If changing behavior in a non-backward compatible way please ensure one
      of the following holds - there is a strong reason to believe no consumers
      depend on a behavior, the behavior is effectively broken, or the API
      method being modified has not been part of a tagged dist release.

The following bullet points represent good practices more than guidelines, please
consider them when modifying the API.

    - Functionality should not be copied and pasted between controllers -
      consider refactoring functionality into associated classes or short of
      that into Mixins (http://en.wikipedia.org/wiki/Composition_over_inheritance)
      or into Managers (:mod:`galaxy.managers`).
    - API additions are more permanent changes to Galaxy than many other potential
      changes and so a second opinion on API changes should be sought.
    - New API functionality should include functional tests. These functional
      tests should be implemented in Python and placed in
      `test/functional/api`.
    - Changes to reflect modifications to the API should be pushed upstream to
      the BioBlend project if possible.

Longer term goals/notes.

    - It would be advantageous to have a clearer separation of anonymous and
      admin handling functionality.
    - If at some point in the future, functionality needs to be added that
      breaks backward compatibility in a significant way to a component used by
      the community - a "dev" variant of the API will be established and
      the community should be alerted and given a timeframe for when the old
      behavior will be replaced with the new behavior.
    - Consistent standards for range-based requests, batch requests, filtered
      requests, etc... should be established and documented here.
