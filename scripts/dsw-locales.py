import click
import pathlib
import requests


class APIClient:

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({'Authorization': f'Bearer {api_key}'})

    def get_locales(self):
        r = self._session.get(
            url=f'{self.api_url}/locales',
            params={'size': 1000},
        )
        r.raise_for_status()
        return r.json()['_embedded']['locales']

    def get_locale(self, locale_uuid: str):
        r = self._session.get(
            url=f'{self.api_url}/locales/{locale_uuid}',
        )
        r.raise_for_status()
        return r.json()

    def get_locale_by_id(self, locale_id: str):
        locales = self.get_locales()
        for locale in locales:
            if locale['id'] == locale_id:
                return self.get_locale(locale['uuid'])
        raise ValueError(f'Locale with id {locale_id} not found')

    def delete_locales(self, locale_id: str):
        org, loc, version = locale_id.split(':')
        r = self._session.delete(
            url=f'{self.api_url}/locales',
            params={'organizationId': org, 'localeId': loc},
        )
        r.raise_for_status()

    def delete_locale(self, locale_uuid: str):
        r = self._session.delete(f'{self.api_url}/locales/{locale_uuid}')
        r.raise_for_status()

    def push_locale(self, data: bytes):
        r = self._session.post(
            url=f'{self.api_url}/locales/bundle',
            files={'file': data},
        )
        r.raise_for_status()
        return r.json()

    def enable_locale(self, locale_uuid: str):
        r = self._session.put(
            url=f'{self.api_url}/locales/{locale_uuid}',
            json={
                'enabled': True,
                'defaultLocale': False,
            },
        )
        r.raise_for_status()
        return r.json()


@click.group()
@click.option('--api-url', envvar='DSW_API_URL', required=True,
              help='URL of the DSW API')
@click.option('--api-key', envvar='DSW_API_KEY', required=True,
              help='API Key for the DSW API')
@click.pass_context
def cli(ctx, api_url: str, api_key: str):
    ctx.obj['api'] = APIClient(api_url, api_key)


@cli.command()
@click.pass_context
def list(ctx):
    api = ctx.obj['api']

    locales = api.get_locales()
    for locale in locales:
        locale_full = api.get_locale(locale['uuid'])
        print(locale_full['id'], locale_full['uuid'], locale_full['versions'])


@cli.command()
@click.option('-o', '--organization-id', is_flag=False, default='*')
@click.option('-l', '--locale-id', is_flag=False, default='*')
@click.option('-y', '--confirm-yes', is_flag=True)
@click.pass_context
def clear(ctx, organization_id: str, locale_id: str, confirm_yes: bool):
    api = ctx.obj['api']

    confirm = confirm_yes
    if not confirm_yes:
        confirm = click.confirm('Are you sure you want to delete all locales?')
    if not confirm:
        return

    locales = api.get_locales()
    for locale in locales:
        org = locale['organizationId']
        loc = locale['localeId']
        version = locale['version']
        coords = f'{org}:{loc}:{version}'
        locale_uuid = locale['uuid']
        if organization_id != '*' and organization_id != org:
            click.echo(f'Skipping {coords} [{locale_uuid}] (different organization)')
            continue
        if locale_id != '*' and locale_id != loc:
            click.echo(f'Skipping {coords} [{locale_uuid}] (different locale)')
            continue

        if locale['defaultLocale']:
            click.echo(f'Skipping {coords} [{locale_uuid}] (default locale)')
            continue
        api.delete_locales(coords)
        click.echo(f'Deleted {coords} [{locale_uuid}] (with all versions)')


@cli.command()
@click.argument('locale_id')
@click.option('-a', '--all-versions', is_flag=True,
              help='Delete all versions of the locale')
@click.pass_context
def delete(ctx, locale_id, all_versions):
    api = ctx.obj['api']

    if all_versions:
        api.delete_locales(locale_id)
        click.echo('Locale and all versions deleted')
    else:
        locale = api.get_locale_by_id(locale_id)
        api.delete_locate(locale['uuid'])
        click.echo('Locale deleted')


@cli.command()
@click.argument('zip_file',
                type=click.Path(exists=True, dir_okay=False, resolve_path=True, allow_dash=True))
@click.option('-e', '--enable', is_flag=True, help='Enable the locale after pushing')
@click.pass_context
def push(ctx, zip_file: str, enable: bool):
    api = ctx.obj['api']

    data = pathlib.Path(zip_file).read_bytes()
    locale = api.push_locale(data)
    click.echo('Locale pushed')

    if enable:
        api.enable_locale(locale['uuid'])
        click.echo('Locale enabled')


if __name__ == '__main__':
    cli(obj={})
