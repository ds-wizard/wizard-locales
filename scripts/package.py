"""Package a locale directory into PO files ready for upload to Wizard (v5.0+).

Replaces @ds-wizard/locale-packager. Since Wizard 5.0, a locale is a single PO
file per component (UI and mail templates) and all metadata is taken from the
PO header:

  Project-Id-Version  <kind>:<version>, e.g. dsw-client:5.0.0 (taken from POT)
  Language            locale code, e.g. cs or pt-BR (from locale.json)
  X-Display-Name      name shown to users (from locale.json)

Usage:
  python scripts/package.py locales/cs -o out/
  python scripts/package.py locales/cs -o out/ --prefix dsw_cs_5.0.0_

Only the Python standard library is used.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent

# PO file in locale dir -> POT file in repository root
COMPONENTS = {
    'wizard.po': 'wizard.pot',
    'mail.po': 'mail.pot',
}

_QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _unescape(value: str) -> str:
    replacements = {'n': '\n', 't': '\t', 'r': '\r', '"': '"', '\\': '\\'}
    return re.sub(r'\\(.)', lambda m: replacements.get(m.group(1), m.group(1)), value)


def _escape(value: str) -> str:
    return (value.replace('\\', '\\\\').replace('"', '\\"')
            .replace('\t', '\\t').replace('\r', '\\r').replace('\n', '\\n'))


def _split_header(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Split PO lines into (comments before header, header entry, rest)."""
    start = None
    for i, line in enumerate(lines):
        if line.startswith('msgid ""'):
            start = i
            break
        if line.strip() and not line.startswith('#'):
            break
    if start is None:
        raise ValueError('missing PO header entry (msgid "")')
    end = start + 1
    while end < len(lines) and lines[end].strip():
        end += 1
    return lines[:start], lines[start:end], lines[end:]


def _parse_header_fields(header: list[str]) -> list[tuple[str, str]]:
    text = ''
    in_msgstr = False
    for line in header:
        stripped = line.strip()
        if stripped.startswith('msgstr'):
            in_msgstr = True
        elif not stripped.startswith('"'):
            in_msgstr = False
        if in_msgstr:
            text += ''.join(_unescape(m) for m in _QUOTED.findall(stripped))
    fields = []
    for field_line in text.split('\n'):
        if ':' in field_line:
            name, value = field_line.split(':', 1)
            fields.append((name.strip(), value.strip()))
    return fields


def _render_header(fields: list[tuple[str, str]]) -> list[str]:
    return ['msgid ""', 'msgstr ""'] + [f'"{_escape(f"{k}: {v}")}\\n"' for k, v in fields]


def read_header_fields(path: pathlib.Path) -> dict[str, str]:
    lines = path.read_text(encoding='utf-8').splitlines()
    _, header, _ = _split_header(lines)
    return dict(_parse_header_fields(header))


def stamp_po(content: str, updates: dict[str, str]) -> str:
    """Return PO content with header fields set (replaced in place or appended)."""
    lines = content.lstrip('\ufeff').splitlines()
    comments, header, rest = _split_header(lines)
    fields = _parse_header_fields(header)
    remaining = dict(updates)
    fields = [(k, remaining.pop(k) if k in remaining else v) for k, v in fields]
    fields.extend(remaining.items())
    return '\n'.join(comments + _render_header(fields) + rest) + '\n'


def to_language_tag(code: str) -> str:
    """Convert directory-style code (pt_BR, zh_Hant) to BCP 47 (pt-BR, zh-Hant)."""
    return code.replace('_', '-')


def package_locale(locale_dir: pathlib.Path, output_dir: pathlib.Path,
                   prefix: str = '', root_dir: pathlib.Path = ROOT_DIR) -> list[pathlib.Path]:
    locale_json = locale_dir / 'locale.json'
    if not locale_json.is_file():
        raise FileNotFoundError(f'{locale_json} not found')
    meta = json.loads(locale_json.read_text(encoding='utf-8'))
    code = meta.get('code') or locale_dir.name
    name = meta.get('name')
    if not name:
        raise ValueError(f'{locale_json}: missing "name"')

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for po_name, pot_name in COMPONENTS.items():
        po_file = locale_dir / po_name
        if not po_file.is_file():
            print(f'- {po_file}: not found, skipping', file=sys.stderr)
            continue
        pot_fields = read_header_fields(root_dir / pot_name)
        pot_version = pot_fields.get('Project-Id-Version', '')
        if ':' not in pot_version:
            raise ValueError(f'{pot_name}: invalid Project-Id-Version "{pot_version}"')
        updates = {
            'Project-Id-Version': pot_version,
            'Language': to_language_tag(code),
            'X-Display-Name': name,
        }
        if pot_fields.get('POT-Creation-Date'):
            updates['POT-Creation-Date'] = pot_fields['POT-Creation-Date']
        content = stamp_po(po_file.read_text(encoding='utf-8'), updates)
        out_file = output_dir / f'{prefix}{po_name}'
        out_file.write_text(content, encoding='utf-8')
        print(f'- {po_file} -> {out_file} ({pot_version}, {updates["Language"]}, {name})')
        outputs.append(out_file)
    if not outputs:
        raise FileNotFoundError(f'no PO files found in {locale_dir}')
    return outputs


def main():
    parser = argparse.ArgumentParser(description='Package locale PO files for Wizard 5.0+')
    parser.add_argument('locale_dir', type=pathlib.Path, help='Locale directory, e.g. locales/cs')
    parser.add_argument('-o', '--output', type=pathlib.Path, default=pathlib.Path('out'),
                        help='Output directory (default: out)')
    parser.add_argument('-p', '--prefix', default='',
                        help='Prefix for output file names, e.g. dsw_cs_5.0.0_')
    args = parser.parse_args()
    try:
        package_locale(args.locale_dir, args.output, args.prefix)
    except (OSError, ValueError) as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
