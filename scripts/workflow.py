import json
import os
import pathlib
import subprocess

import click
import dotenv
import requests


SCRIPTS_DIR = pathlib.Path(__file__).parent
dotenv.load_dotenv(SCRIPTS_DIR / '.env')

WEBLATE_PROJECT_WEB_URL = 'https://ds-wizard.org'


class WeblateClient:

    def __init__(self, base_url: str, api_token: str,
                 session: requests.Session | None = None):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = session or requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {self.api_token}',
        })

    def _url(self, path: str) -> str:
        return f'{self.base_url}/api/{path}'

    def lock_component(self, project_slug: str, component_slug: str) -> bool:
        r = self.session.post(
            url=self._url(f'projects/{project_slug}/components/{component_slug}/lock/'),
            json={
                'lock': True,
            }
        )
        r.raise_for_status()
        return r.json().get('lock', False)

    def get_project(self, project_slug: str) -> dict:
        r = self.session.get(
            url=self._url(f'projects/{project_slug}/'),
        )
        r.raise_for_status()
        return r.json()

    def get_project_components(self, project_slug: str) -> list[dict]:
        r = self.session.get(
            url=self._url(f'projects/{project_slug}/components/'),
        )
        r.raise_for_status()
        return r.json().get('results', [])

    def create_project(self, name: str, slug: str) -> dict:
        r = self.session.post(
            url=self._url('projects/'),
            json={
                'name': name,
                'slug': slug,
                'web': WEBLATE_PROJECT_WEB_URL,
                'check_flags': '',
                'translation_review': False,
                'source_review': False,
                'set_language_team': True,
                'instructions': '',
                'enable_hooks': True,
                'language_aliases': '',
                'secondary_language': 0,
                'enforced_2fa': False
            },
        )
        r.raise_for_status()
        return r.json()

    def create_component(self, project_slug: str, name: str, slug: str, branch: str,
                         po_filemask: str, pot_file: str, repoweb: str) -> dict:
        r = self.session.post(
            url=self._url(f'projects/{project_slug}/components/'),
            json={
              'name': name,
              'slug': slug,
              'source_language': {
                  'code': 'en',
                  'name': 'English',
                  'plural': {
                      'source': 0,
                      'number': 2,
                      'formula': 'n != 1'
                  },
                  'direction': 'ltr',
                  'population': 1728003224
              },
              'vcs': 'git',
              'repo': 'git@github.com:ds-wizard/wizard-locales.git',
              'git_export': f'https://localize.ds-wizard.org/git/{project_slug}/{slug}/',
              'branch': branch,
              'push_branch': branch,
              'filemask': po_filemask,
              'screenshot_filemask': '',
              'template': '',
              'edit_template': True,
              'intermediate': '',
              'new_base': pot_file,
              'file_format': 'po',
              'license': 'CC-BY-4.0',
              'agreement': '',
              'new_lang': 'add',
              'language_code_style': '',
              'push': 'git@github.com:ds-wizard/wizard-locales.git',
              'check_flags': '',
              'priority': 100,
              'enforced_checks': [],
              'restricted': False,
              'repoweb': repoweb,
              'report_source_bugs': '',
              'merge_style': 'rebase',
              'commit_message': 'Translated using Weblate ({{ language_name }})\n\nCurrently translated at {{ stats.translated_percent }}% ({{ stats.translated }} of {{ stats.all }} strings)\n\nTranslation: {{ project_name }}/{{ component_name }}\nTranslate-URL: {{ url }}',
              'add_message': 'Added translation using Weblate ({{ language_name }})\n\n',
              'delete_message': 'Deleted translation using Weblate ({{ language_name }})\n\n',
              'merge_message': 'Merge branch \'{{ component_remote_branch }}\' into Weblate.\n\n',
              'addon_message': 'Update translation files\n\nUpdated by \"{{ addon_name }}\" add-on in Weblate.\n\nTranslation: {{ project_name }}/{{ component_name }}\nTranslate-URL: {{ url }}',
              'pull_message': 'Translations update from {{ site_title }}\n\nTranslations update from [{{ site_title }}]({{ site_url }}) for [{{ project_name }}/{{ component_name }}]({{url}}).\n\n{% if component_linked_childs %}\nIt also includes following components:\n{% for linked in component_linked_childs %}\n* [{{ linked.project_name }}/{{ linked.name }}]({{ linked.url }})\n{% endfor %}\n{% endif %}\n\nCurrent translation status:\n\n![Weblate translation status]({{widget_url}})\n',
              "allow_translation_propagation": True,
              "manage_units": False,
              "enable_suggestions": True,
              "suggestion_voting": False,
              "suggestion_autoaccept": 0,
              'push_on_commit': True,
              'commit_pending_age': 24,
              'auto_lock_error': True,
              'language_regex': '^[^.]+$',
              'key_filter': '',
              'secondary_language': None,
              'variant_regex': '',
              'zipfile': '',
              'docfile': '',
              'is_glossary': False,
              'glossary_color': 'silver',
              'disable_autoshare': True,
              'category': None,
            },
        )
        r.raise_for_status()
        return r.json()


def _parse_version(version: str) -> tuple[int, int, int]:
    parts = version.split('.')
    if len(parts) != 3:
        raise ValueError('Version must be in the format X.Y.Z')
    major, minor, patch = parts
    return int(major), int(minor), int(patch)


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


def _create_weblate_project(weblate_client: WeblateClient, project_name: str, project_slug: str):
    click.echo(f'Creating Weblate project "{project_name}" with slug "{project_slug}"')
    project = weblate_client.create_project(name=project_name, slug=project_slug)
    click.echo(f'Created project: {json.dumps(project, indent=2)}')
    client_component = weblate_client.create_component(
        project_slug=project_slug,
        name='DSW Locales',
        slug='dsw-locales',
        branch='main',
        po_filemask='locales/{locale}/LC_MESSAGES/dsw.po',
        pot_file='locales/dsw.pot',
        repoweb='https://localize.ds-wizard.org/git/{project_slug}/{component_slug}/',
    )
    mail_template_component = weblate_client.create_component(
        project_slug=project_slug,
        name='DSW Mail Templates',
        slug='dsw-mail-templates',
        branch='main',
        po_filemask='mail-templates/{locale}/LC_MESSAGES/dsw-mail-templates.po',
        pot_file='mail-templates/dsw-mail-templates.pot',
        repoweb='https://localize.ds-wizard.org/git/{project_slug}/{component_slug}/',
    )
    return project


def _release(version: str, locales_dir: pathlib.Path):
    weblate_client = WeblateClient(
        base_url=os.getenv('WEBLATE_BASE_URL', ''),
        api_token=os.getenv('WEBLATE_API_TOKEN', ''),
    )
    major, minor, patch = _parse_version(version)
    # Prepare local environment
    click.echo('Locking changes in project on Weblate')
    # TODO: weblate lock (API only via all component)
    click.echo('Pushing changes from Weblate')
    # TODO: push changes from Weblate
    click.echo('Waiting for change propagation')
    click.echo('Checking out the correct branch')
    _run('git', 'checkout', f'v{major}.{minor}')
    click.echo('Pulling latest changes')
    _run('git', 'pull', 'origin', f'v{major}.{minor}')

    # Update version in locale.json files
    langs = []
    for locale_dir in locales_dir.iterdir():
        if not locale_dir.is_dir():
            continue
        locale_id = locale_dir.name
        locale_json = locale_dir / 'locale.json'
        if not locale_json.is_file():
            click.echo(f'Warning: locale.json not found for locale {locale_id}, skipping', err=True)
            continue
        data = json.loads(locale_json.read_text(encoding='utf-8'))
        process = click.prompt(f'Do you want to release locale {locale_id}?',
                               show_default=True, type=bool, default=True)
        if not process:
            click.echo(f'Skipping locale {locale_id}')
            continue
        langs.append(locale_id)
        click.echo(f'Processing locale {locale_id}')
        data['version'] = version
        data['recommendedAppVersion'] = f'{major}.{minor}.0'
        locale_json.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        click.echo(f'Updated version in {locale_json}')

    # Let user do manual changes
    click.echo('You can now make any manual changes to the locale files if necessary.')
    proceed = False
    while not proceed:
        proceed = click.prompt('Are you ready to continue with the release process?',
                               show_default=True, type=bool, default=True)

    # Commit and push changes
    click.echo('Committing all changes')
    _run('git', 'add', '-A')
    _run('git', 'commit', '-m', f'Release {version} ({', '.join(langs)})')
    click.echo('Pushing changes to remote')
    _run('git', 'push', 'origin', f'v{major}.{minor}')
    click.echo('Creating git tags')
    for lang in  langs:
        tag_name = f'v{version}-{lang}'
        click.echo(f'Creating tag {tag_name}')
        _run('git', 'tag', tag_name)
        _run('git', 'push', 'origin', tag_name)


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
@click.argument('old_version')
@click.argument('new_version')
def prepare(old_version: str, new_version: str):
    ...


@cli.command()
def test():
    weblate_client = WeblateClient(
        base_url=os.getenv('WEBLATE_BASE_URL', ''),
        api_token=os.getenv('WEBLATE_API_TOKEN', ''),
    )
    result = weblate_client.get_project('dsw-4-25')
    print('Project info:')
    print(json.dumps(result, indent=2))
    components = weblate_client.get_project_components('dsw-4-25')
    print(f'Found {len(components)} components:')
    print(json.dumps(components, indent=2))


if __name__ == '__main__':
    cli()
