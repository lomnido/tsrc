[![image](https://img.shields.io/github/license/your-tools/tsrc.svg)](https://github.com/your-tools/tsrc/blob/main/LICENSE)

[![image](https://github.com/your-tools/tsrc/workflows/tests/badge.svg)](https://github.com/your-tools/tsrc/actions)

[![image](https://github.com/your-tools/tsrc/workflows/linters/badge.svg)](https://github.com/your-tools/tsrc/actions)

[![image](https://img.shields.io/pypi/v/tsrc.svg)](https://pypi.org/project/tsrc/)

[![image](https://img.shields.io/badge/deps%20scanning-pyup.io-green)](https://github.com/your-tools/tsrc/actions)

# tsrc: manage groups of git repositories

[Overview](#overview) · [Installation](#installation) · [Usage example](#usage-example) · [Documentation](#documentation) · [Release notes](#release-notes) · [Contributing](#contributing) · [License](#license)

## Note

This project was originally hosted on the [TankerHQ](https://github.com/TankerHQ) organization, which was my employer from 2016 to 2021. They kindly agreed to give back ownership of this project to me. Thanks!

## Overview

tsrc is a command-line tool that helps you manage groups of several git
repositories.

It can be [seen in action on asciinema.org](https://asciinema.org/a/131625).

## Note

<span class="title-ref">tsrc</span> does not adhere strictly to the [semver specification](https://semver.org/). So before upgrading to a new version, please take the time to read the [Changelog](https://your-tools.github.io/tsrc/changelog/) first!

## Installation

The recommended way to install `tsrc` is to use [pipx](https://pipxproject.github.io/pipx/).

* Make sure to have Python **3.7** or later installed.
* Install `pipx`
* Run `pipx install tsrc`.

## Usage Example

  - Create a *manifest* repository. (`git@example.org/manifest.git`)
  - Add a file named `manifest.yml` at the root of the *manifest*
    repository.

`manifest.yml`:

``` yaml
repos:
  - url: git@example.com/foo.git
    dest: foo

 -  url: git@example.com/bar.git
    dest: bar
```

It is convenient while optional to include the manifest repository itself in your `manifest.yml`. It will allow you to have a local copy of you manifest repository to easily make changes to it in the future.

  - commit your `manifest.yml` and push the changes to the manifest
    repository.
  - Create a new workspace with all the repositories listed in the
    manifest:

``` console
$ tsrc init git@git.local/manifest.git

:: Configuring workspace in /path/to/work
...
=> Cloning missing repos
* (1/2) foo
...
* (2/2) bar
...
: Configuring remotes
Done ✓
```

  - Synchronize all the repositories in the workspace:

``` console
$ tsrc sync
=> Updating manifest
...
:: Configuring remotes
:: Synchronizing workspace
* (1/2) foo
=> Fetching origin
=> Updating branch
Already up to date
* (2/2) bar
=> Updating branch
Updating 29ac0e1..b635a43
Fast-forward
 bar.txt | 1 +
 1 file changed, 1 insertion(+)
 create mode 100644 bar.txt
Done ✓
```

## Documentation

For more details and examples, please refer to [tsrc documentation](https://your-tools.github.io/tsrc/).

## Release notes

Detailed changes for each release are documented in the [changelog](https://your-tools.github.io/tsrc/changelog/).

## Contributing

We welcome feedback, [bug reports](https://github.com/your-tools/tsrc/issues), and bug fixes in the form of [pull requests](https://github.com/your-tools/tsrc/pulls).

Detailed instructions can be found [in the documentation](https://your-tools.github.io/tsrc).

## License

tsrc is licensed under a [BSD 3-Clause license](https://github.com/your-tools/tsrc/blob/main/LICENSE).
