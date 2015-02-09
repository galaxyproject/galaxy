# Contributing

This document briefly describes how to contribute to the
galaxy-central core project - also checkout our 2013 Galaxy Community
Conference presentation] on the topic
([video](http://vimeo.com/channels/581875/73486255),
[presentation](https://wiki.galaxyproject.org/Documents/Presentations/GCC2013?action=AttachFile&do=view&target=BakerContribute.pdf)). For
information on contributing more broadly to the Galaxy ecosystem and a
deeper discussion of some of these points - please see the
[Develop](https://wiki.galaxyproject.org/Develop/) section of the
[Galaxy Wiki](https://wiki.galaxyproject.org/).

## Before you Begin

If you have an idea for a feature to add or an approach for a bugfix -
it is best to communicate with Galaxy developers early. The most
common venue for this is the [Galaxy Trello
board](https://wiki.galaxyproject.org/Issues). Browse through existing
cards [here](http://bit.ly/gxytrello) and if one seems related comment
on it. If no existing cards seem appropriate, a new issue can be
opened using [this form](http://galaxyproject.org/trello). Galaxy
developers are also generally available via
[IRC](https://wiki.galaxyproject.org/GetInvolved#IRC_Channel) and on
the [development mailing list](http://dev.list.galaxyproject.org/).

## How to Contribute

* If you are new to Mercurial - please check out this [official
  tutorial](http://mercurial.selenic.com/wiki/Tutorial)

* Make sure you have a free [Bitbucket
  account](https://bitbucket.org/account/signup/)

* Fork the galaxy-central repository on
  [Bitbucket](https://bitbucket.org/galaxy/galaxy-central/fork) to
  make your changes. (Many Galaxy instances target
  [galaxy-dist](https://bitbucket.org/galaxy/galaxy-dist) - but active
  development happens on galaxy-central and this is where pull
  requests should be made).

* Choose the correct Mercurial branch to develop your changes against.

  * Additions to the code base should be pushed to the `default`
    branch (`hg checkout default`).

  * Most bug fixes to previously release components (things in
    galaxy-dist) should be pushed to the `stable` branch (`hg checkout
    stable`).

  * Serious security problems should not be fixed via pull request -
    please responsibly disclose these by e-mailing them (with or
    without patches) to galaxy-lab@bx.psu.edu. The Galaxy core
    development team will issue patches to public servers before
    announcing the issue to ensure there is time to patch and
    highlight these fixes widely. We will provide you credit for the
    discovery when publicly disclosing the issue.

* If your changes modify code - please ensure the resulting files
  conform to Galaxy [style
  guidelines](https://wiki.galaxyproject.org/Develop/BestPractices).

* Galaxy contains hundreds of tests of different types and complexity
  and running each is difficult and probably not reasonable at this
  time (someday we will provide a holistic test procedure to make this
  possible). For now, please just review the [running tests
  documentation](https://wiki.galaxyproject.org/Admin/RunningTests)
  and run any that seem relevant. Developers reviewing your pull
  request will be happy to help guide you to running the most relevant
  tests as part of the pull request review process and may request the
  output of these tests.

* Commit and push your changes to your Bitbucket fork.

* Open a [pull
  request](https://confluence.atlassian.com/display/BITBUCKET/Fork+a+Repo,+Compare+Code,+and+Create+a+Pull+Request)
  with these changes. You pull request message should include:

   * A description of why the change should be made.
   
   * A description of implementation of the change.
   
   * A description of how to test the change.

## Ideas

Galaxy's [Trello board](http://bit.ly/gxytrello) is filled with bugs and ideas
for enhancements, but we maintain a [card](https://trello.com/c/eFdPIdIB) with
links to smaller issues we believe would make the best entry points for new
developers.

## A Quick Note about Tools

  For the most part, Galaxy tools should be published to the
  [ToolShed](https://wiki.galaxyproject.org/ToolShed) and not in this
  repository directly. If you are looking to supply fixes for migrated
  core tools that used to exist in this repository - please checkout
  the [tools-devteam](https://github.com/galaxyproject/tools-devteam)
  repository on GitHub.

  More information about tool development can be found [on the
  wiki](https://wiki.galaxyproject.org/Develop).
