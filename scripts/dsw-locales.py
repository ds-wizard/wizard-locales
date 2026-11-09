"""Manage locales in a Wizard instance (v5.0+).

Since Wizard 5.0, UI locales (/locales) and mail template locales
(/mail-template-locales) are separate resources, each uploaded as a single PO
file. A locale is identified by its language code (from the PO header);
uploading a PO with an existing code replaces it in place.

DSW_API_URL must point to the API root including the /api prefix,
e.g. https://example.ds-wizard.org/api
"""
import pathlib

import click
import requests

KINDS = {
    'ui': 'locales',
    'mail': 'mail-template-locales',
}
# Default kind by PO file name
FILE_KINDS = {
    'wizard.po': 'ui',
    'mail.po': 'mail',
}


def normalize_code(code: str) -> str:
    return code.replace('_', '-').lower()


class APIClient:

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip('/')
        self._session = requests.Session()
        self._session.headers.update({'Authorization': f'Bearer {api_key}'})

    def _url(self, kind: str, *parts: str) -> str:
        return '/'.join([self.api_url, KINDS[kind], *parts])

    def get_locales(self, kind: str) -> list[dict]:
        r = self._session.get(self._url(kind))
        r.raise_for_status()
        return r.json()

    def find_locale(self, kind: str, code: str) -> dict | None:
        for locale in self.get_locales(kind):
            if normalize_code(locale['code']) == normalize_code(code):
                return locale
        return None

    def upload_locale(self, kind: str, filename: str, data: bytes) -> dict:
        r = self._session.post(
            url=self._url(kind),
            files={'file': (filename, data, 'text/x-gettext-translation')},
            data={'confirmed': 'true'},
        )
        if not r.ok:
            raise click.ClickException(f'Upload failed ({r.status_code}): {r.text}')
        return r.json()

    def update_locale(self, kind: str, locale: dict, enabled: bool) -> dict:
        r = self._session.put(
            url=self._url(kind, locale['uuid']),
            json={
                'enabled': enabled,
                'defaultLocale': locale['defaultLocale'],
            },
        )
        r.raise_for_status()
        return r.json()

    def delete_locale(self, kind: str, locale_uuid: str):
        r = self._session.delete(self._url(kind, locale_uuid))
        r.raise_for_status()


def _kinds(kind: str) -> list[str]:
    return list(KINDS) if kind == 'all' else [kind]


def _describe(locale: dict) -> str:
    flags = [f for f in ('enabled', 'defaultLocale', 'official') if locale.get(f)]
    return (f'{locale["code"]} "{locale["name"]}" [{locale["uuid"]}] '
            f'{locale.get("potVersion") or "-"} {",".join(flags)}').rstrip()


@click.group()
@click.option('--api-url', envvar='DSW_API_URL', required=True,
              help='URL of the Wizard API (including /api)')
@click.option('--api-key', envvar='DSW_API_KEY', required=True,
              help='API key for the Wizard API')
@click.pass_context
def cli(ctx, api_url: str, api_key: str):
    ctx.obj['api'] = APIClient(api_url, api_key)


kind_option = click.option('-k', '--kind', type=click.Choice(['ui', 'mail', 'all']), default='all',
                           show_default=True, help='Locale kind')


@cli.command(name='list')
@kind_option
@click.pass_context
def list_locales(ctx, kind: str):
    """List locales"""
    api: APIClient = ctx.obj['api']
    for k in _kinds(kind):
        click.echo(f'# {k} ({KINDS[k]})')
        for locale in api.get_locales(k):
            click.echo(_describe(locale))


@cli.command()
@kind_option
@click.option('-c', '--code', default='*', help='Only locales with this code')
@click.option('-y', '--confirm-yes', is_flag=True)
@click.pass_context
def clear(ctx, kind: str, code: str, confirm_yes: bool):
    """Delete locales (except default ones)"""
    api: APIClient = ctx.obj['api']
    if not confirm_yes and not click.confirm('Are you sure you want to delete the locales?'):
        return
    for k in _kinds(kind):
        for locale in api.get_locales(k):
            if code != '*' and normalize_code(locale['code']) != normalize_code(code):
                continue
            if locale['defaultLocale']:
                click.echo(f'Skipping {k} {_describe(locale)} (default locale)')
                continue
            api.delete_locale(k, locale['uuid'])
            click.echo(f'Deleted {k} {_describe(locale)}')


@cli.command()
@click.argument('code')
@kind_option
@click.pass_context
def delete(ctx, code: str, kind: str):
    """Delete locale by code"""
    api: APIClient = ctx.obj['api']
    for k in _kinds(kind):
        locale = api.find_locale(k, code)
        if locale is None:
            click.echo(f'No {k} locale with code {code}')
            continue
        api.delete_locale(k, locale['uuid'])
        click.echo(f'Deleted {k} {_describe(locale)}')


@cli.command()
@click.argument('po_files', nargs=-1, required=True,
                type=click.Path(exists=True, dir_okay=False, resolve_path=True, path_type=pathlib.Path))
@click.option('-k', '--kind', type=click.Choice(['ui', 'mail']), default=None,
              help='Locale kind (default: guessed from file name, *wizard.po = ui, *mail.po = mail)')
@click.option('-e', '--enable', is_flag=True, help='Enable the locale after pushing')
@click.pass_context
def push(ctx, po_files: tuple[pathlib.Path, ...], kind: str | None, enable: bool):
    """Upload PO file(s), replacing existing locales with the same code"""
    api: APIClient = ctx.obj['api']
    for po_file in po_files:
        k = kind or next((v for s, v in FILE_KINDS.items() if po_file.name.endswith(s)), None)
        if k is None:
            raise click.UsageError(f'Cannot guess kind of {po_file.name}, use --kind')
        result = api.upload_locale(k, po_file.name, po_file.read_bytes())
        locale = result['locale']
        action = 'replaced' if result.get('replaced') else 'created'
        click.echo(f'{po_file.name}: {k} locale {action}: {_describe(locale)}')
        if enable and not locale['enabled']:
            locale = api.update_locale(k, locale, enabled=True)
            click.echo(f'{po_file.name}: {k} locale enabled')


if __name__ == '__main__':
    cli(obj={})
