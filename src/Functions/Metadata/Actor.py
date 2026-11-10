"""Conservative actor-name normalization for consistent local person records."""
import unicodedata


def normalize_actors(names, aliases=None):
    if isinstance(names, str):
        names = [names]
    if not isinstance(names, (list, tuple)):
        return []
    aliases = aliases or {}
    result = []
    for name in names:
        if not isinstance(name, str):
            continue
        name = ' '.join(unicodedata.normalize('NFKC', name).split())
        replacement = aliases.get(name, name)
        if not isinstance(replacement, str):
            continue
        name = ' '.join(unicodedata.normalize('NFKC', replacement).split())
        if name and name not in result:
            result.append(name)
    return result
