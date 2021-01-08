A group of new user welcome topics to be displayed the first time a newly registered user logs in, or accessible through the help tab on the Galaxy masthead. This is configurable in the galaxy.yml file.

Basic topics include:
 * **Data**

 * **Tools**   

 * **Workflows**

The standard version of this repo deployed as the npm package: galaxy_new_user_welcome.

To add/remove topis, alter the list of the new_user_welcome_subjects in the galaxy.yml file.

In order to add topics for specialized instances, clone the repo, add a new topic, and edit the galaxy_new_user_package setting in the galaxy.yml file.

When creating a new topic, the following format is used for the json:

```
{
    "title": topic title,
    "image": image file to be used on the menu for overall topic
    "alt": alt text for overall topic image
    "blurb": quick desciption of topic
    "intro": More in-depth text to be displayed viewing the subtopic options
    "topics": [
        {
            "title": "Importing via Data Uploader",
            "header": "Galaxy Data Uploader",
            "image": "upload-solid.svg",
            "alt": "Data Uploader",
            "intro": "Loading in data from your machine or via URL.",
            "slides": [
                {
                    "file": Slide image file, 
                    "size": image size [mini-img, small-img, med-img, large-img],
                    "alt": slide image alt text,
                    "text": slide main text
                },
                ...
        },
        ...
    ]
},
...
```
