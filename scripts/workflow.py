import json
import pathlib
import subprocess

import click

SCRIPTS_DIR = pathlib.Path(__file__).parent


def _parse_version(version: str) -> tuple[int, int, int]:
    parts = version.split('.')
    if len(parts) != 3:
        raise ValueError('Version must be in the format X.Y.Z')
    major, minor, patch = parts
    return int(major), int(minor), int(patch)


def _proceed():
    proceed = False
    while not proceed:
        proceed = click.prompt(
            text='Are you ready to continue?',
            show_default=True,
            type=bool,
            default=True,
        )
    click.echo('=' * 60)


def _run(*command: str) -> None:
    click.echo(f'Running command: {' '.join(command)}')
    try:
        click.echo('-'*40)
        subprocess.run(command, check=True)
        click.echo('-'*40)
    except subprocess.CalledProcessError as e:
        click.echo('-'*40)
        click.echo(f'Error: Command "{" ".join(command)}" failed with exit code {e.returncode}', err=True)
        raise e


def _release(version: str, locales_dir: pathlib.Path):
    major, minor, patch = _parse_version(version)
    # Prepare local environment
    click.echo('WEBLATE: Go to Weblate and ensure everything is synced and ready for release:')
    localize_url = f'https://localize.ds-wizard.org/projects/dsw-{major}-{minor}/#repository'
    click.echo('- 0 in pending')
    click.echo('- 0 in outgoing')
    click.echo('- 0 in missing')
    click.echo('- Lock components all components (click Lock button)')
    click.echo(f'> {localize_url}')
    click.launch(localize_url)
    _proceed()

    # Wait for changes in Git
    click.echo('GITHUB: Go to Git and ensure everything is up to date:')
    commits_url = f'https://github.com/ds-wizard/wizard-locales/commits/v{major}.{minor}/'
    click.echo(f'> {commits_url}')
    click.launch(commits_url)
    click.echo('REPO: Also verify that local git repository without any uncommitted changes.')
    _proceed()

    # Checkout correct branch and pull latest changes
    click.echo('REPO: Checking out the correct branch')
    _run('git', 'checkout', f'v{major}.{minor}')
    click.echo('REPO: Pulling latest changes')
    _run('git', 'pull', 'origin', f'v{major}.{minor}')

    # Update version in locale.json files
    click.echo('REPO: Updating version in locale.json files')
    langs = []
    for locale_dir in sorted(locales_dir.iterdir()):
        if not locale_dir.is_dir():
            continue
        locale_id = locale_dir.name
        locale_json = locale_dir / 'locale.json'
        if not locale_json.is_file():
            click.echo(f'- Warning: locale.json not found for locale {locale_id}, skipping', err=True)
            continue
        data = json.loads(locale_json.read_text(encoding='utf-8'))
        process = click.prompt(f'> Do you want to release locale {locale_id}?',
                               show_default=True, type=bool, default=True)
        if not process:
            click.echo(f'- Skipping locale {locale_id}')
            continue
        langs.append(locale_id)
        click.echo(f'- Processing locale {locale_id}')
        data['version'] = version
        data['recommendedAppVersion'] = f'{major}.{minor}.0'
        locale_json.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        click.echo(f'- Updated version in {locale_json}')

    # Let user do manual changes
    click.echo('REPO: You can now make any manual changes if necessary')
    _proceed()

    # Commit and push changes
    click.echo('REPO: Committing all changes')
    _run('git', 'add', '-A')
    _run('git', 'commit', '-m', f'Release {version} ({', '.join(langs)})')
    click.echo('REPO: Pushing changes to remote')
    _run('git', 'push', 'origin', f'v{major}.{minor}')
    click.echo('REPO: Creating git tags')
    for lang in  langs:
        tag_name = f'v{version}-{lang}'
        click.echo(f'- Creating tag {tag_name}')
        _run('git', 'tag', tag_name)
        _run('git', 'push', 'origin', tag_name)


def _prepare(version: str, locales_dir: pathlib.Path):
    major, minor, patch = _parse_version(version)
    prev_major = major
    prev_minor = minor - 1
    if prev_minor < 0:
        raise ValueError('Previous version minor number cannot be less than 0')
    # Prepare local environment
    click.echo('REPO: Make sure everything locally is committed and pushed to remote:')
    click.echo(f'- You should be on v{prev_major}.{prev_minor} branch')
    click.echo(f'- No uncommitted changes should be present')
    _proceed()

    # Checkout correct branch and pull latest changes
    click.echo('REPO: Checking out the correct branch')
    _run('git', 'checkout', f'v{prev_major}.{prev_minor}')
    click.echo('REPO: Pulling latest changes')
    _run('git', 'pull', 'origin', f'v{prev_major}.{prev_minor}')
    click.echo('REPO: Creating new branch for the new version')
    _run('git', 'checkout', '-b', f'v{major}.{minor}')
    click.echo('REPO: Pushing new branch to remote')
    _run('git', 'push', '-u', 'origin', f'v{major}.{minor}')

    # Create Weblate project
    click.echo('WEBLATE: Create new Weblate project for the new version:')
    weblate_url = 'https://localize.ds-wizard.org/create/project/'
    click.echo(f'> {weblate_url}')
    click.launch(weblate_url)
    click.echo('Make sure to set the following parameters:')
    click.echo(f'- Name: DSW {major}.{minor}')
    click.echo(f'- Project: https://ds-wizard.org')
    _proceed()
    click.echo('WEBLATE: Component "Client"')
    click.echo('- repo URL: git@github.com:ds-wizard/wizard-locales.git')
    click.echo(f'- branch: v{major}.{minor}')
    click.echo('- Specify configuration manually')
    click.echo('- push URL and push branch same as repo URL and branch')
    suffix = '/{{filename}}#L{{line}}'
    click.echo(f'- repository browser: https://github.com/ds-wizard/engine-frontend/tree/v{major}.{minor}.0{suffix}')
    click.echo('- file format: gettext PO (no line wrapping + keep msgids)')
    click.echo('- file mask: locales/*/wizard.po')
    click.echo('- template for new translations: wizard.pot')
    _proceed()
    click.echo('WEBLATE: Component "Mail Templates"')
    click.echo('- repo URL: git@github.com:ds-wizard/wizard-locales.git')
    click.echo(f'- branch: v{major}.{minor}')
    click.echo('- Specify configuration manually')
    click.echo('- push URL and push branch same as repo URL and branch')
    click.echo('- file format: gettext PO (no line wrapping + keep msgids)')
    click.echo('- file mask: locales/*/mail.po')
    click.echo('- template for new translations: mail.pot')
    click.echo('WEBLATE: Share Glossary')
    click.echo('- Go to Glossary tab and share glossary with the new project')
    glossary_url = 'https://localize.ds-wizard.org/settings/glossary/glossary/'
    click.echo(f'> {glossary_url}')
    click.launch(glossary_url)
    _proceed()
    click.echo('WEBLATE: Wait for Weblate to finish initial synchronization and check that everything is correct')
    click.echo('- sync all changes Weblate might have done')
    settings_url = f'https://localize.ds-wizard.org/projects/dsw-{major}-{minor}/#repository'
    click.echo(f'> {settings_url}')
    click.launch(settings_url)
    click.echo('REPO: Prepare for new POT files:')
    frontend_url = 'https://github.com/ds-wizard/engine-frontend/tags'
    tools_url = 'https://github.com/ds-wizard/engine-tools/tags'
    click.echo('- Download wizard.pot to repository from engine-frontend latest release')
    click.echo(f'> {frontend_url}')
    click.launch(frontend_url)
    click.echo('- Download mail.pot to repository from engine-frontend latest release')
    click.echo(f'> {tools_url}')
    click.launch(tools_url)
    _proceed()
    click.echo('REPO: Commit and push POT file updates')
    _run('git', 'add', 'wizard.pot', 'mail.pot')
    _run('git', 'commit', '-m', f'Update POT files to v{major}.{minor}')
    _run('git', 'push', 'origin', f'v{major}.{minor}')
    click.echo('Preparation for new version completed successfully.')


@click.group()
def cli():
    """Utilities for managing locales workflow"""
    pass


@cli.command()
@click.argument('version')
def release(version: str):
    """Create a new locales release"""
    directory = pathlib.Path.cwd()
    locales_dir = directory / 'locales'
    if not locales_dir.is_dir():
        click.echo('Error: locales directory not found', err=True)
        click.echo('Make sure to run this command from the project root directory', err=True)
        return
    try:
        _release(version, locales_dir)
    except Exception:
        import traceback
        traceback.print_exc()
        click.echo('Failed to create release', err=True)
        return


@cli.command()
@click.argument('version')
def prepare(version: str):
    """Prepare for a new locales version"""
    directory = pathlib.Path.cwd()
    locales_dir = directory / 'locales'
    if not locales_dir.is_dir():
        click.echo('Error: locales directory not found', err=True)
        click.echo('Make sure to run this command from the project root directory', err=True)
        return
    try:
        _prepare(version, locales_dir)
    except Exception:
        import traceback
        traceback.print_exc()
        click.echo('Failed to prepare for new version', err=True)
        return


if __name__ == '__main__':
    cli()
