# Wizard Locales

*Localization of DSW user interface and mail templates*

[![LICENSE](https://img.shields.io/github/license/ds-wizard/wizard-client-localization)](LICENSE)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/4975/badge)](https://bestpractices.coreinfrastructure.org/projects/4975)

## Contributing

### How to Contribute

There are two ways how to contribute:

1. Use service **[localize.ds-wizard.org](https://localize.ds-wizard.org)** that we managed and is linked with this repository.
2. Use your own tool for translation (such as [Poedit](https://poedit.net/)) and contribute using `git` and GitHub directly via [Pull Request](https://docs.github.com/en/pull-requests).

If you want to start contributing, please let us know via email, Slack channel, or issue in this repo.

#### Using localize.ds-wizard.org

We host service **[localize.ds-wizard.org](https://localize.ds-wizard.org)** which is an instance of [Weblate](https://weblate.org/) for DSW projects. In general, please check the [official documentation](https://docs.weblate.org/en/latest/) whenever needed. The service is linked to this repository and automatically synchronizes. A component in the service refers to a specific version of Wizard Client (e.g. `3.17.1`); thus a branch in this repository.

To contribute, please follow this:

* Use your real name in the registration.
* Use your email that you also use on GitHub / link more emails and GitHub account (that will allow to link commits to your GitHub account).
* Translate whatever you can and are confident with, otherwise feel free to use suggestions or mark as check needed.
* (recommended) Use [Gravatar](https://en.gravatar.com/) with your photo or preferred profile image.

If you get lost or stuck, just ask via Slack or email.

#### Using GitHub

It is possible to contribute also directly to this GitHub repository via [Pull Request](https://docs.github.com/en/pull-requests). Simply edit or create `.po` file, commit and push it to your fork, and then submit the pull request. Please follow the repository structure that we keep here (described below).

To stay consistent, please do not use any line wrap in gettext files.

Another forms of contributions via GitHub such as issues with reports and suggestions are also highly appreciated.

### Community of DSW Translators

We cherish the community of translators as it is a significant contribution to DSW open-source and also committment to help maintain the locale in future versions. For efficient communication, translators use a dedicated Slack channel which is possible to join by request.

### Repository Structure

We keep the directory structure as follows:

* `locales/`
  * `<lang-code>/` = directory for a single language
    * `locale.json` = locale metadata file
    * `mail.po` = locale messages (PO) file for mail templates of `mailer`
    * `wizard.po` = locale messages (PO) file for `wizard-client`
    * `README.md` = basic information about locale, contributors and changelog
* `LICENSE` = license text for all locales
* `README.md` = this file
* `mail.pot` = source (POT) file for mail templates messages
* `wizard.pot` = source (POT) file for `wizard-client` messages

It is important to keep the structure consistent across all languages. The repository maintainers will take care of metadata and information about locales and ask contributors for details if needed.

For each Wizard Client version, there is a separate branch in this repository. That allows to develop locales also for historical versions even if a newer version is released. Everytime a new version of Wizard Client is released, a new branch is created from the previous version-branch, and POT filesare updated; then all PO files are refreshed (`msgmerge`) together with locales metadata and READMEs. Then, translation work can continue. In [localize.ds-wizard.org](https://localize.ds-wizard.org), a new component is added according to the version.

## References and Resources

* [GNU GetText](https://www.gnu.org/software/gettext/manual/index.html)
* [Weblate documentation](https://docs.weblate.org/en/latest/)
* [DS Wizard](https://ds-wizard.org)
* [DSW Registry (Locales)](https://registry.ds-wizard.org/locales)

## License

This project is licensed under the [Creative Commons Attribution 4.0 (CC-BY-4.0)](https://creativecommons.org/licenses/by/4.0/) - see the [LICENSE](LICENSE) file for more details.
