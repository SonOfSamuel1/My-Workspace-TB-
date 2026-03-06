"""ActionOS dashboard shell builder.

Renders the parent shell page: sidebar, header with quick-add bar,
and iframes for all ActionOS views. All iframes point back to the
same unified Lambda function URL.
"""

import html
from typing import List, Tuple

_FONT = (
    "'Inter','SF Pro Display',-apple-system,BlinkMacSystemFont,"
    "'Segoe UI',Roboto,sans-serif"
)


def build_shell_html(
    function_url: str,
    action_token: str,
    starred_count: int,
    projects: List[dict] = None,
    vapid_public_key: str = "",
) -> str:
    """Build the ActionOS shell page with sidebar + iframes.

    Args:
        function_url: The unified Lambda function URL (base).
        action_token: Auth token for all action links.
        starred_count: Number of starred email tasks (for initial badge).
        projects: List of Todoist project dicts for quick-add dropdown.
        vapid_public_key: VAPID public key for push subscriptions.
    """
    base = function_url.rstrip("/")

    # All tab URLs point to the same Lambda with view= param
    # Lazy-load strategy: only the first tab (Home) preloads at page load.
    # All others load on first switchTab() call.
    tabs: List[Tuple[str, str, str, bool]] = [
        ("home", "Home", f"{base}?action=web&view=home&embed=1", True),
        ("focus", "Focus", f"{base}?action=web&view=focus&embed=1", False),
        ("godpower", "God Power", f"{base}?action=web&view=godpower&embed=1", False),
        ("commit", "Commit", f"{base}?action=web&view=commit&embed=1", False),
        ("starred", "Starred", f"{base}?action=web&view=starred&embed=1", False),
        ("unread", "Unread", f"{base}?action=web&view=unread&embed=1", False),
        ("inbox", "Inbox", f"{base}?action=web&view=inbox&embed=1", False),
        ("p1", "P1", f"{base}?action=web&view=p1&embed=1", False),
        ("p1nodate", "P1 No Date", f"{base}?action=web&view=p1nodate&embed=1", False),
        ("bestcase", "Best Case", f"{base}?action=web&view=bestcase&embed=1", False),
        ("calendar", "Calendar", f"{base}?action=web&view=calendar&embed=1", False),
        ("followup", "Follow-up", f"{base}?action=web&view=followup&embed=1", False),
        ("sabbath", "Sabbath", f"{base}?action=web&view=sabbath&embed=1", False),
        ("code", "Code", f"{base}?action=web&view=code&embed=1", False),
        ("activitylog", "Activity Log", f"{base}?action=web&view=activitylog&embed=1", False),
    ]

    # Generate sidebar tab HTML
    sidebar_tabs_html = ""
    for i, (tid, label, _url, _preload) in enumerate(tabs):
        active = " active" if i == 0 else ""
        badge_text = str(starred_count) if tid == "starred" else "..."
        if tid == "commit":
            badge_html = (
                f'<span style="display:flex;align-items:center;gap:4px;">'
                f'<span class="badge badge-due-today" id="badge-{tid}-due-today" style="display:none"></span>'
                f'<span class="badge" id="badge-{tid}">{badge_text}</span>'
                f"</span>"
            )
        else:
            badge_html = f'<span class="badge" id="badge-{tid}">{badge_text}</span>'
        sidebar_tabs_html += (
            f'<div class="sidebar-tab{active}" id="tab-{tid}" '
            f'draggable="true" data-tab-id="{tid}" onclick="switchTab(\'{tid}\')">'
            f'<span class="tab-label">{label}</span>'
            f"{badge_html}"
            f"</div>"
        )

    # Generate iframe HTML (lazy: non-first tabs use dark placeholder)
    # Use srcdoc with matching background instead of about:blank to
    # prevent white flash while iframe content loads from Lambda.
    _dark_srcdoc = (
        "<html><head><style>"
        "html,body{margin:0;background:#1a1a1a;color-scheme:dark}"
        "@media(prefers-color-scheme:light){html,body{background:#eeeef0;color-scheme:light}}"
        "</style></head><body></body></html>"
    )
    iframes_html = ""
    for i, (tid, _label, url, preload) in enumerate(tabs):
        display = "" if i == 0 else "display:none;"
        _bg_style = "background:#1a1a1a;color-scheme:dark;"
        if preload:
            iframes_html += (
                f'<iframe id="frame-{tid}" src="{url}" style="{display}{_bg_style}"'
                f' data-src="{url}"></iframe>'
            )
        else:
            iframes_html += (
                f'<iframe id="frame-{tid}" srcdoc="{html.escape(_dark_srcdoc)}" style="{display}{_bg_style}"'
                f' data-src="{url}"></iframe>'
            )

    # Tab URLs JSON for lazy loading
    tab_urls_json = (
        "{" + ",".join(f'"{tid}":"{url}"' for tid, _label, url, _preload in tabs) + "}"
    )

    # Tab IDs array
    tab_ids_json = "[" + ",".join(f'"{tid}"' for tid, *_ in tabs) + "]"

    # Mobile dropdown items
    first_label = tabs[0][1]
    first_badge = "..."
    # Per-section SVG icons (20x20, stroke-based)
    _section_icons = {
        "home": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
        "starred": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
        "unread": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
        "inbox": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>',
        "commit": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
        "p1": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>',
        "p1nodate": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="9" y1="14" x2="15" y2="20"/><line x1="15" y1="14" x2="9" y2="20"/></svg>',
        "bestcase": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3z"/><path d="M19 15l.5 2 2 .5-2 .5-.5 2-.5-2-2-.5 2-.5.5-2z"/></svg>',
        "calendar": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
        "sabbath": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2c-1 4-4 6-4 10a4 4 0 0 0 8 0c0-4-3-6-4-10z"/><line x1="12" y1="16" x2="12" y2="22"/></svg>',
        "code": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
        "followup": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 17 4 12 9 7"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/></svg>',
    }
    dropdown_items_html = ""
    for i, (tid, label, _url, _preload) in enumerate(tabs):
        active_cls = " active" if i == 0 else ""
        icon_svg = _section_icons.get(tid, "")
        badge_init = str(starred_count) if tid == "starred" else "..."
        if tid == "commit":
            badge_group = (
                f'<span style="display:flex;align-items:center;gap:4px;">'
                f'<span class="badge badge-due-today section-dropdown-badge" id="dpbadge-{tid}-due-today" style="display:none"></span>'
                f'<span class="badge section-dropdown-badge" id="dpbadge-{tid}">{badge_init}</span>'
                f"</span>"
            )
        else:
            badge_group = f'<span class="badge section-dropdown-badge" id="dpbadge-{tid}">{badge_init}</span>'
        dropdown_items_html += (
            f'<div class="section-dropdown-item{active_cls}" data-tab-id="{tid}" '
            f"onclick=\"selectSection('{tid}')\">"
            f'<span class="section-dropdown-icon">{icon_svg}</span>'
            f'<span class="section-dropdown-label">{label}</span>'
            f"{badge_group}"
            f'<span class="section-dd-arrows">'
            f'<button class="section-dd-arrow" onclick="event.stopPropagation();moveSectionUp(\'{tid}\')">&#9650;</button>'
            f'<button class="section-dd-arrow" onclick="event.stopPropagation();moveSectionDown(\'{tid}\')">&#9660;</button>'
            f"</span>"
            f"</div>"
        )

    # Quick-add project dropdown options
    project_options_html = '<option value="">Inbox</option>'
    if projects:
        for p in projects:
            pid = p.get("id", "")
            pname = p.get("name", "")
            project_options_html += f'<option value="{pid}">{pname}</option>'

    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<link rel="icon" type="image/png" href="data:image/png;base64,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">'
        '<link rel="apple-touch-icon" href="data:image/png;base64,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">'
        '<link rel="manifest" href="data:application/manifest+json,%7B%22name%22%3A%22ActionOS%22%2C%22short_name%22%3A%22ActionOS%22%2C%22description%22%3A%22Personal%20action%20dashboard%22%2C%22icons%22%3A%5B%7B%22src%22%3A%22data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAABS3GwHAAAABmJLR0QA%2FwD%2FAP%2BgvaeTAAAOSUlEQVR4nO3dbWxUV3oH8P9zx8b2jO8YwkviidINodjbYDAom1CFIN7a3ara7a7U1b60AlbZVittQ1etoBL5FqUkUqFVl0RRV1rYNv0U0jYKTdtVqpBFOCsS0mBvYneBQNTEmERAgufO2MbxzNMP4wEM9rx45t6Dz%2Fn%2FvjFz77kPw%2Fkzz71zXwQGBUGwJJ%2BXNYB2Al4noJ0iWAJoApAFABIA5pmskWo2DiAL6GeAZFXxCSCngfyvVeVULKYnfd%2B%2FaKo4iXJjQ0Mab20d%2BV0R3ayKTQC6oq6BbjsK4F0RvK4qR3w%2F%2Ft8iMhrVxkOffKrqBUHwMCBbAfkOgGTY26Q5LQ3gZUBe9P34f4pILsyNhRYAVW3OZDKPqspOAEvD2g7ZTM%2BJYF9ra%2BtBEbkaxhbqHoBCm5P9IYC%2FBNBe7%2FHJSRcA7MtkEv%2BQSslIPQeuawDS6ezXAN0P4N56jks0aVBE%2F8L3%2FX%2Bp14B1CcBnn43eG4vlngHw1XqMR1SaHp6YaNhxxx0tH9Y6Us0BSKez3wD0IIAFtY5FVIW0iP6p7%2FuHahnEm%2B2KqtoUBJkfA%2FoSOPkpeklVeSGdDn6iqk2zHWRW3wDpdHohIK8A8tuz3TBR%2FcgbqhN%2F0NbW9mnVa1a7QjabTeVy%2BnMAK6tdlyhE%2F9vQ4H0lHo9%2FVM1KVQUgnU5%2FUdV7VQT3VFcbUfhE8KFq%2FsvJZPJUxetUuuDIyMjdExP5NwB8YVbVEUXjfC4XW7dgQcv%2FVbJwRQEo9PzeMQC%2FVVNpRNEYUM2tr2SfoOxRoMIetrwCTn6aO%2B4X8f69kqNDZQOQTo%2F8LY%2F20NwjD2cy2b8pu1SpN4Mg%2BKaqvFi%2FooiiJaJ%2F6Pv%2Bv834%2FkxvTJ7e0AugLZTKiKJxJZeLrZ5pp3jGFigWy%2B0HJz%2FNffNjsYkfz%2FTmtAEonN%2BDr4VWElGk5OuFM5WneefmFybP5x8Aj%2FeTXT7w%2FcSKmy%2B3vOUboLU1%2B2fg5Cf7LE2nsz%2B4%2BcUp3wCFMzyz5wCkIiuLKDoXfD9xn4iMFV%2BY8g2QyWS%2BD05%2Bsld7JjOy%2FcYXrn0DFO7ekH0fvICdrCZnfT%2B%2BXEQUuOEbIJPJbAAnP1lPl2UymfXFP10LgKpsNVMQUbRUcW2uS%2BEFbQmC7AXwhy9yQ9r3E3eJyKgHAEEw8mVw8pM7kun0yGZgsgUS0c1m6yGKlohuAiYDMHmjWiJnqGILAEgQBEtU5WPwLs3kljyQv9Mr3J%2Bfk5%2Bc43met9orPJyCyD2q2ukVnsxC5CKv0wO0w3QZRGZopyeCu0yXQWSCKu7yAPimCyEyxGcAyGW%2BB6DVdBVEhvge%2BBxeclfTrB%2BQQWQDBoCcxgCQ0xgAchoDQE5jAMhpDAA5jQEgpzEA5DQGgJzWYLqA28XExAQ%2B%2BuhDZLMjpksJVSIRxz33%2FAYaGvhPDzAAAIAjR17DoUMvIAgC06VEwvd9fOtb38bmzVtMl2Kc8wH4xS9ex4EDPzVdRqSCIMCBAz%2BF53nYuNHtO%2BI4vQ8wPj6OQ4deMF2GMYcOvYDx8XHTZRjldAD6%2BnoxPDxsugxjhoeH8atf9ZkuwyinA%2FDmm2%2BaLsE41z8DZwMwPj6OkyffMV2Gce%2B88z9Ot0HOBqCvrxdjY2PlF7Tc2NiY022QswFw%2Fav%2FRi5%2FFk4eBq2k%2FWlpacHu3bshMrdvm6qqePrppzE6OjrjMsU2aN489y4PdzIAlbQ%2Fa9euxerVqyOqKFwPPfQQjh49OuP7xTboS196MMKqbg9OtkCVfOWvW7cugkqiUcnfxdU2yLkAjI%2BPo7f3ZMllWlpasGbNmogqCt8DDzyAeDxechlXjwY5F4C%2Bvt6S%2FTBQaH9s6ocbGxvx4IOl2xtXjwY5FwDX2p8itkHTcyoALrY%2FRWyDpudUAFxsf4rYBk3PqQC42v4UsQ26lTMBcLn9KWIbdCtnAuBy%2B1PENuhWzgTA9faniG3QVE4EgO3PdWyDpnIiAGx%2FrmMbNJUTAWD7MxXboOusDwDbn1uxDbrO%2BgCw%2FbkV26DrrA8A25%2FpsQ0qsDoAbH9mxjaowOoAsP2ZGdugAqsDwPanNLZBFgeA7U95bIMsDgDbn%2FLYBlkcALY%2FlXG9DbIyAGx%2FKud6G2RlANj%2BVM71NsjKALD9qY7LbZB1AWD7Uz2X2yDrAsD2p3out0HWBYDtz%2By42gZZFQC2P7PnahtkVQDY%2Fsyeq22QVQFg%2B1MbF9sga54PUEn709TUhIaGBvT12fW%2FWL00Njaiubm55LMTbHuYhjUBqKT9uXr1Kp544omIKrKTbQ%2FTsKYFOnz4sOkSnHH48MumS6gbKwIwNjaGc%2BfOmi7DGWfPnrXmCZtWBIA9ffRs%2BcytCEA2mzFdgnNs%2BcytCMDixUtMl%2BAcWz5zKwIQi8WgqqbLcIaqIhaLmS6jLqwIAIA5%2F0DrucSmz9qa3wHKefTRR7F06VLTZcwJH3zwAQ4ePGi6jEg4E4Bly5Zh5cqVpsuYEzzPmsagLHf%2BpkTTYADIaQwAOY0BIKcxAOQ0BoCcxgCQ05z5HaBeent70dPTg%2F7%2Bfly%2BfBkAsGjRItx%2F%2F%2F1Yv349uru7b%2BvxaSoGoELnz5%2FHs88%2Bi%2F7%2B%2FlveGxwcxODgIF599VV0dXXhscceQyqVuq3Gp%2BmxBapAf38%2Fdu3aNe3kvNl7772HnTt3VrRsVOPTzBiAMs6fP489e%2FYgk6n8%2FPdMJoOnnnoKFy5cMD4%2BlcYAlPHcc89VNTmLgiDA%2Fv37jY9PpTEAJfT29uLdd9%2Bd9fr9%2Ff0lLx0Me3wqjwEo4dixYzWP0dPTY2x8Ko8BKGFgYKDmMUrtrIY9PpXHAJRQPA5fi0uXLhkbn8pjAEIW9sUlLl28EgZ%2BeiUsXLgw1DHCHp%2FKYwBKWLFiRahjhD0%2BlccAlLB%2B%2Ffqax3jkkUeMjU%2FlMQAldHd3Y9WqVbNev6urq%2BT6YY9P5TEAZezYsQPJZLLq9Xzfx44dO4yPT6UxAGXceeed2L17N3zfr3gd3%2Ffx%2BOOPo7293fj4VBoDUIEVK1Zg7969Fd1XaOXKldi3b19VO6dhj08z4%2FUAFUqlUtizZw%2F6%2BvrQ09ODgYEBXLx4EQCwePHiaxeszLYnD3t8mh4DUKXu7u5Qr8oKe3yaii0QOY0BIKcxAOQ0BoCcZkUAmprKP7T5888%2Fj6ASO4yPj5ddppLPfC6wIgDxeKLsMp9%2B%2BmkEldihkusUEonWCCoJnxUBaGtrK%2FvYnuPHj0dUzdxX7rMSEbS1tUVUTbis%2BB0gHo%2Bjvb0dQ0NDMy7z1ltv4cknn8TatWuxaNEiax7yVi%2B5XA6XLl3C8ePH8fbbb5dcNpVKoaWlJaLKwmVFAACgo6OzZAAA4MSJEzhx4kREFdmro6PTdAl1Y0ULBAAbNmw0XYIzNmzYYLqEurEmAB0dHVi%2BfLnpMqzX2dmJ5cs7TJdRN9YEAAC2bduOxsZG02VYa968edi6dZvpMurKqgDcd98ybNu23XQZ1tq%2B%2FXtYuvQ%2B02XUlTU7wUWbN29BY2MjDh48UNEPOlReY2MjvvvdP8LGjZtMl1J3kk5n1HQRYTh37iyef%2F6fcObMGdOlzGmdnZ3YunWbdf%2FzF1kbgKIzZ07j6NGjOH36FIaGhqBq9V%2B3ZiKCVCqFjo5ObNiwwaod3ulYH4AbjY6OYnh4GNlsBqOjY6bLua20tDQjkWjF%2FPnz0dzcbLqcyDgVAKKbWXUUiKhaDAA5jQEgpzEA5DQPAH8tIldd9QBU%2F4hCIjsEHoDAdBVEhjAA5LTAU8XHpqsgMkEEH3uAnDZdCJEZcsoD8qdMl0FkRv6UBwgDQE4SkVMSBMFiVfkEQOkb6xDZJQ%2Fkl3i%2B718E8J7paoiipIq%2BZDJ52QMAERwxXRBRlIpz3gMAVWEAyCnFOS%2BFP2hLEGQvALDjho9EpQ37fqJdREYnWyAZBfCvhosiiogempzz10%2BHFtF%2FNlcQUZSuz%2FVrhz5V1QuCzBlA7Lz%2FBREAQN73%2FXiHiCgw5RtA8iLYZ64wovCJYG9x8gM3%2Ffilqk1BkD0HIBV5ZUThG%2FT9xG%2BKyNXiC1MuiZx84%2B8iL4soAqq698bJD0xz%2BsPQkMZbW7P9AO6NqjCi8MlZ3493iciUO6LdclF8KiUjqvLD6AojCp8qfnTz5AdmuCtEW1vivwA9HH5ZRFHQl9raEv8x3Tsz3hZlYqJhB4ArodVEFI3PGhpiP5rpzRkDcMcdLR8CshUA7x1Kc5UC3vfj8fhHMy1Q8sZYyWTiFRE8U%2F%2B6iCLx98lk%2FKVSC5S9CKbw20DmCCAP168uotAd8%2F3E74hIyRu%2Flb01oohcnZj4%2FPcB9NWtNKJw9avmvlFu8gNVXAY5MjJy98RE%2Fg0AX6ipNKJwDU5MxNYV9mHLq%2FjmuPF4%2FDyQ%2F4oIKhqYKGqFuZnfUunkB2ZxIXw2m23P5fTnAFZVuy5RiAYaGrzfK3XEZzpV3x49kUhcUM1tAvSX1a5LFJJj%2BfzEI9VOfqCGW6GoakMQZP8awF%2FVMg5RDVQEz7S2JnZVssM7nZonbjqd%2FTqgPwOwoNaxiKqQFtE%2F8X3%2FxVoGqfkJMclk4uVcLraG5w5RdPSlhgavq9bJD9S5dUmns18FdD%2BApfUcl6hAz6l6fz7TiW2zUffeXVVb0unsD0SwE8Dd9R6fnDSoin3JZOIn053SXIvQdl5VtSmTGfmeKnYBuiys7ZDN5H0R7G1tjf%2FjbHdyy24hjEFvduVK9oFYTLep4o8BLIximzRnDQM47Hl4PpFIvHbjBexhiPTwpao2p9MjW0R0iyo2iWAV%2BKhW1%2BVV0SeC11XltWQyfqTebU4pRo%2Ffp9PpRfm8tyYW0w7A%2ByKgnapYAqgPyHwArQDmmayRajYOIAPoFUACEXxSeCpR%2Ftciciqfz59MJpOXTRX3%2F859nMDkX5LJAAAAAElFTkSuQmCC%22%2C%22sizes%22%3A%22192x192%22%2C%22type%22%3A%22image%2Fpng%22%2C%22purpose%22%3A%22any%20maskable%22%7D%5D%2C%22theme_color%22%3A%22%233d1b42%22%2C%22background_color%22%3A%22%231a1a1a%22%2C%22display%22%3A%22standalone%22%2C%22orientation%22%3A%22portrait%22%2C%22start_url%22%3A%22.%22%7D">'
        '<meta name="apple-mobile-web-app-capable" content="yes">'
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
        '<meta name="apple-mobile-web-app-title" content="ActionOS">'
        '<meta name="theme-color" content="#3d1b42">'
        '<meta http-equiv="Cache-Control" content="no-cache">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link rel="preconnect" href="https://api.todoist.com">'
        '<link rel="preload" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" as="style" onload="this.onload=null;this.rel=\'stylesheet\'">'
        '<noscript><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet"></noscript>'
        "<title>ActionOS</title>"
        "<style>"
        ":root{"
        "--bg-base:#1a1a1a;--bg-s0:#1c1c1e;--bg-s1:#252528;--bg-s2:#2c2c2e;"
        "--text-1:#ffffff;--text-2:#8e8e93;--text-3:#48484a;"
        "--border:rgba(255,255,255,0.08);--border-h:rgba(255,255,255,0.12);"
        "--accent:#6366f1;--accent-l:#818cf8;"
        "--accent-bg:rgba(99,102,241,0.10);--accent-b:rgba(99,102,241,0.20);"
        "--accent-hbg:rgba(99,102,241,0.08);"
        "--ok:#22c55e;--ok-bg:rgba(34,197,94,0.10);--ok-b:rgba(34,197,94,0.20);"
        "--warn:#eab308;--warn-bg:rgba(234,179,8,0.10);--warn-b:rgba(234,179,8,0.20);"
        "--err:#ef4444;--err-bg:rgba(239,68,68,0.10);--err-b:rgba(239,68,68,0.20);"
        "--purple:#a78bfa;--purple-bg:rgba(167,139,250,0.10);--purple-b:rgba(167,139,250,0.20);"
        "--fab-bg:#db4035;--scrollbar:rgba(255,255,255,0.10);color-scheme:dark;}"
        "@media(prefers-color-scheme:light){:root{"
        "--bg-base:#eeeef0;--bg-s0:#fff;--bg-s1:#fff;--bg-s2:#f5f5f7;"
        "--text-1:#202124;--text-2:#5f6368;--text-3:#80868b;"
        "--border:rgba(0,0,0,0.08);--border-h:rgba(0,0,0,0.15);"
        "--accent:#6366f1;--accent-l:#4f46e5;"
        "--accent-bg:rgba(99,102,241,0.08);--accent-b:rgba(99,102,241,0.15);"
        "--accent-hbg:rgba(99,102,241,0.06);"
        "--ok:#188038;--ok-bg:#e6f4ea;--ok-b:rgba(24,128,56,0.20);"
        "--warn:#e37400;--warn-bg:#fef7e0;--warn-b:rgba(227,116,0,0.20);"
        "--err:#d93025;--err-bg:#fce8e6;--err-b:rgba(217,48,37,0.20);"
        "--purple:#7c4dff;--purple-bg:#ede7f6;--purple-b:rgba(124,77,255,0.20);"
        "--fab-bg:#2d3561;--scrollbar:rgba(0,0,0,0.12);color-scheme:light;}}"
        "*{box-sizing:border-box;margin:0;padding:0;}"
        "body{font-family:" + _FONT + ";background:var(--bg-base);"
        "-webkit-font-smoothing:antialiased;}"
        ".header{background:var(--bg-s0);border-bottom:1px solid var(--border);padding:10px 20px;display:flex;"
        "align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;}"
        ".header-title-link{color:var(--text-1);font-size:17px;font-weight:600;letter-spacing:-0.2px;"
        "text-decoration:none;cursor:pointer;}"
        ".header-title-link:hover{color:var(--accent-l);}"
        ".due-today-badge{display:inline-flex;align-items:center;gap:4px;background:var(--ok-bg);color:var(--ok);"
        "font-size:12px;font-weight:700;padding:3px 10px;border-radius:12px;border:1px solid var(--ok-b);"
        "margin-left:10px;white-space:nowrap;}"
        ".due-today-badge.zero{background:var(--border);color:var(--text-2);border-color:var(--border);}"
        ".next-pending-btn{background:var(--accent-bg);border:1.5px solid var(--accent);color:var(--accent);"
        "font-size:13px;font-weight:600;padding:0 14px;border-radius:20px;cursor:pointer;"
        "display:inline-flex;align-items:center;gap:5px;white-space:nowrap;min-height:44px;flex-shrink:0;}"
        ".next-pending-btn:hover{opacity:0.75;}"
        "#shell-next-label{background:rgba(0,0,0,0.25);border-radius:999px;"
        "min-width:18px;height:18px;display:inline-flex;align-items:center;"
        "justify-content:center;font-size:10px;font-weight:700;color:#fff;padding:0 4px;}"
        ".refresh-btn{background:var(--border);border:1px solid var(--border);color:var(--text-1);"
        "font-size:13px;font-weight:600;padding:6px 14px;border-radius:6px;cursor:pointer;flex-shrink:0;}"
        ".refresh-btn:hover{background:var(--border-h);}"
        ".notif-btn{background:transparent;border:none;color:var(--text-2);cursor:pointer;"
        "width:32px;height:32px;border-radius:6px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}"
        ".notif-btn:hover{background:var(--border);color:var(--text-1);}"
        ".notif-btn.active{color:var(--accent-l);}"
        ".header-actions{display:flex;align-items:center;gap:4px;}"
        # Quick-add bar (below header)
        ".quick-add-bar{background:var(--bg-s1);border-bottom:1px solid var(--border);"
        "padding:8px 16px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;}"
        ".quick-add-input{flex:1;min-width:160px;font-family:inherit;font-size:13px;padding:6px 10px;"
        "border:1px solid var(--border-h);border-radius:6px;background:var(--bg-s2);color:var(--text-1);}"
        ".quick-add-input:focus{outline:none;border-color:rgba(99,102,241,0.5);}"
        ".quick-add-select{font-family:inherit;font-size:12px;padding:5px 8px;"
        "border:1px solid var(--border);border-radius:6px;background:var(--bg-s2);color:var(--text-1);cursor:pointer;}"
        ".quick-add-btn{font-family:inherit;font-size:13px;font-weight:600;padding:6px 16px;"
        "border-radius:6px;background:var(--accent-bg);color:var(--accent-l);"
        "border:1px solid var(--accent-b);cursor:pointer;white-space:nowrap;}"
        ".quick-add-btn:hover{background:var(--accent-b);}"
        ".quick-add-btn:disabled{opacity:0.5;cursor:default;}"
        # App body
        ".app-body{display:flex;overflow:hidden;"
        "height:calc(100vh - 48px - 44px - 68px);}"  # header + quick-add bar + floating bottom nav
        ".sidebar{width:180px;min-width:180px;background:var(--bg-s0);"
        "border-right:1px solid var(--border);display:flex;flex-direction:column;"
        "overflow-y:auto;user-select:none;}"
        ".sidebar-tab{display:flex;align-items:center;justify-content:space-between;"
        "padding:14px 16px;font-size:14px;font-weight:600;color:var(--text-2);"
        "cursor:pointer;border-left:3px solid transparent;transition:color .15s ease-out,background .15s ease-out,border-color .15s ease-out;}"
        ".sidebar-tab:hover{background:var(--bg-s2);}"
        ".sidebar-tab.active{color:var(--text-1);background:var(--accent-hbg);border-left-color:var(--accent);}"
        ".badge{display:inline-block;background:var(--border);color:var(--text-2);font-size:11px;"
        "font-weight:700;padding:2px 8px;border-radius:10px;}"
        ".sidebar-tab.active .badge{background:var(--accent-bg);color:var(--accent-l);}"
        ".badge-due-today{background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn-b);}"
        ".sidebar-tab.active .badge-due-today{background:var(--warn-bg);color:var(--warn);}"
        ".sidebar-tab.dragging{opacity:0.4;}"
        ".sidebar-tab.drag-over{border-top:2px solid var(--accent);}"
        ".tab-label-input{font:inherit;font-size:14px;font-weight:600;width:80px;"
        "border:1px solid var(--accent);border-radius:3px;padding:1px 4px;outline:none;"
        "background:var(--bg-s2);color:var(--text-1);}"
        ".main-content{flex:1;position:relative;overflow:hidden;background:var(--bg-base);}"
        ".main-content iframe{display:block;position:absolute;top:0;left:0;width:100%;height:100%;"
        "border:none;background:var(--bg-base);color-scheme:dark;}"
        # Mobile section picker
        ".section-picker{display:none;align-items:center;gap:8px;background:var(--bg-s2);"
        "border:1px solid var(--border-h);border-radius:8px;padding:7px 12px 7px 14px;"
        "cursor:pointer;touch-action:manipulation;}"
        ".section-picker-label{font-size:14px;font-weight:600;color:var(--text-1);}"
        ".section-picker-chevron{font-size:11px;color:var(--text-2);margin-left:2px;}"
        ".section-dropdown{display:none;position:fixed;top:56px;left:16px;right:16px;z-index:9999;"
        "background:var(--bg-s1);border:1px solid var(--border-h);"
        "border-radius:14px;"
        "box-shadow:0 8px 32px rgba(0,0,0,.25), 0 2px 8px rgba(0,0,0,.15);"
        "overflow:hidden;max-height:calc(100dvh - 72px);overflow-y:auto;"
        "will-change:transform,opacity;}"
        ".section-dropdown.open{display:block;animation:ddSlide .15s ease;}"
        "@keyframes ddSlide{from{opacity:0;transform:translateY(-8px) scale(.97)}to{opacity:1;transform:translateY(0) scale(1)}}"
        ".section-dropdown-item{display:flex;align-items:center;gap:14px;padding:13px 18px;"
        "font-size:15px;font-weight:500;color:var(--text-2);cursor:pointer;"
        "touch-action:manipulation;transition:background .12s ease;}"
        ""
        ".section-dropdown-item.active{color:var(--text-1);background:var(--accent-hbg);border-radius:10px;margin:2px 4px;}"
        ".section-dropdown-icon{width:22px;height:22px;flex-shrink:0;color:var(--text-2);display:flex;align-items:center;justify-content:center;}"
        ".section-dropdown-item.active .section-dropdown-icon{color:var(--accent-l);}"
        ".section-dropdown-label{flex:1;}"
        ".section-dropdown-badge{margin-left:auto;}"
        ".section-dd-header{display:flex;align-items:center;justify-content:space-between;padding:14px 18px 10px;border-bottom:1px solid var(--border);}"
        ".section-dd-title{font-size:13px;font-weight:600;color:var(--text-2);text-transform:uppercase;letter-spacing:.5px;}"
        ".section-dd-edit-btn{background:none;border:none;color:var(--accent-l);font-size:14px;font-weight:600;cursor:pointer;}"
        ".section-dd-arrows{display:none;margin-left:auto;gap:4px;}"
        ".section-dropdown.editing .section-dd-arrows{display:flex;}"
        ".section-dropdown.editing .section-dropdown-icon{display:none;}"
        ".section-dropdown.editing .badge{display:none;}"
        ".section-dd-arrow{background:var(--bg-s2);border:1px solid var(--border);color:var(--text-2);"
        "width:32px;height:32px;border-radius:6px;font-size:12px;cursor:pointer;"
        "display:flex;align-items:center;justify-content:center;}"
        ".section-dd-arrow:active{background:var(--accent-bg);color:var(--accent-l);}"
        ".section-dd-rename-input{font:inherit;font-size:15px;font-weight:500;"
        "border:1px solid var(--accent);border-radius:4px;padding:2px 8px;"
        "background:var(--bg-s2);color:var(--text-1);outline:none;width:120px;}"
        ".section-dropdown-backdrop{display:none;position:fixed;inset:0;z-index:9998;}"
        ".section-dropdown-backdrop.open{display:block;}"
        # FAB + bottom sheet (mobile quick-add) - Todoist-style
        ".qa-fab{display:none;position:fixed;bottom:88px;right:20px;width:56px;height:56px;"
        "border-radius:50%;background:var(--fab-bg);color:#fff;"
        "border:none;cursor:pointer;align-items:center;justify-content:center;"
        "box-shadow:0 2px 8px rgba(0,0,0,.25);z-index:1000;touch-action:manipulation;}"
        ".cal-fab{display:none;position:fixed;bottom:156px;right:20px;width:56px;height:56px;"
        "border-radius:50%;background:var(--fab-bg);color:#fff;"
        "align-items:center;justify-content:center;"
        "box-shadow:0 2px 8px rgba(0,0,0,.25);z-index:1000;text-decoration:none;touch-action:manipulation;}"
        ".qa-sheet-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);"
        "z-index:1001;}"
        ".qa-sheet-overlay.open{display:block;}"
        ".qa-sheet{position:fixed;bottom:0;left:0;right:0;background:#fff;"
        "border-radius:16px 16px 0 0;padding:10px 16px 0;z-index:1002;"
        "will-change:transform;transform:translateY(100%);transition:transform .28s cubic-bezier(.4,0,.2,1);"
        "box-shadow:0 -4px 16px rgba(0,0,0,.2);}"
        ".qa-sheet.open{transform:translateY(0);}"
        ".qa-sheet-handle{width:36px;height:4px;background:#e0e0e0;"
        "border-radius:2px;margin:0 auto 14px;}"
        ".qa-sheet-task{width:100%;font-family:inherit;font-size:17px;font-weight:500;"
        "background:transparent;border:none;color:#202020;"
        "caret-color:var(--fab-bg);outline:none;padding:4px 0;}"
        ".qa-sheet-task::placeholder{color:#bbb;}"
        ".qa-sheet-desc{width:100%;font-family:inherit;font-size:14px;"
        "background:transparent;border:none;color:#555;"
        "caret-color:var(--fab-bg);outline:none;resize:none;padding:2px 0;"
        "min-height:20px;max-height:80px;display:block;}"
        ".qa-sheet-desc::placeholder{color:#ccc;}"
        ".qa-sheet-icons{display:flex;gap:6px;padding:12px 0;"
        "border-top:1px solid #f0f0f0;margin-top:10px;}"
        ".qa-icon-btn{width:36px;height:36px;border-radius:50%;border:none;"
        "background:#f5f5f5;color:#888;cursor:pointer;display:flex;"
        "align-items:center;justify-content:center;flex-shrink:0;touch-action:manipulation;}"
        ".qa-icon-btn svg{width:18px;height:18px;}"
        ".qa-icon-btn.active-date{background:#fff3e0;color:#f57c00;}"
        ".qa-icon-btn.active-p1{background:#ffebee;color:#e53935;}"
        ".qa-icon-btn.active-p2{background:#fff3e0;color:#f57c00;}"
        ".qa-icon-btn.active-p3{background:#e3f2fd;color:#1e88e5;}"
        ".qa-icon-btn.active-commit{background:#fff3e0;color:#f57c00;}"
        ".qa-icon-btn.active-bestcase{background:#f3e5f5;color:#ab47bc;}"
        ".qa-sheet-bottom{display:flex;align-items:center;justify-content:space-between;"
        "padding:8px 0 env(safe-area-inset-bottom,20px);border-top:1px solid #f0f0f0;margin-top:4px;}"
        ".qa-sheet-inbox-area{display:flex;align-items:center;gap:6px;color:#555;}"
        ".qa-sheet-inbox-area svg{width:18px;height:18px;flex-shrink:0;}"
        ".qa-sheet-project{font-family:inherit;font-size:14px;color:#333;"
        "background:transparent;border:none;outline:none;cursor:pointer;max-width:200px;"
        "appearance:none;-webkit-appearance:none;}"
        ".qa-sheet-send{width:40px;height:40px;border-radius:50%;background:#272f3e;"
        "border:none;color:#fff;cursor:pointer;display:flex;"
        "align-items:center;justify-content:center;"
        "box-shadow:0 2px 8px rgba(0,0,0,.3);flex-shrink:0;transition:opacity .15s;}"
        ".qa-sheet-send:disabled{opacity:.35;}"
        # Hide iOS search clear button that appears on type="search" inputs
        "input[type=search]::-webkit-search-cancel-button{display:none;}"
        "input[type=search]::-webkit-search-decoration{display:none;}"
        "@media(prefers-color-scheme:dark){"
        ".qa-sheet{background:#272727;}"
        ".qa-sheet-handle{background:#444;}"
        ".qa-sheet-task{color:#f0f0f0;}"
        ".qa-sheet-task::placeholder{color:#555;}"
        ".qa-sheet-desc{color:#aaa;}"
        ".qa-sheet-desc::placeholder{color:#444;}"
        ".qa-sheet-icons{border-top-color:#383838;}"
        ".qa-icon-btn{background:#383838;color:#999;}"
        ".qa-icon-btn.active-date{background:#3d2e10;color:#f57c00;}"
        ".qa-icon-btn.active-p1{background:#3d1515;color:#e53935;}"
        ".qa-icon-btn.active-p2{background:#3d2e10;color:#f57c00;}"
        ".qa-icon-btn.active-p3{background:#102036;color:#1e88e5;}"
        ".qa-icon-btn.active-commit{background:#3d2e10;color:#f57c00;}"
        ".qa-icon-btn.active-bestcase{background:#2e1040;color:#ab47bc;}"
        ".qa-sheet-bottom{border-top-color:#383838;}"
        ".qa-sheet-inbox-area{color:#aaa;}"
        ".qa-sheet-project{color:#ccc;}"
        "}"
        "@media(max-width:768px){"
        ".header{flex-wrap:nowrap;padding:10px 16px;gap:12px;"
        "background:transparent;border-bottom:none;align-items:center;}"
        ".header-title-link{display:none;}"
        ".due-today-badge{margin-left:0;font-size:11px;padding:2px 8px;}"
        ".section-picker{display:flex;border:none;border-radius:20px;"
        "background:var(--bg-s1);border:1px solid var(--border);"
        "height:44px;padding:0 14px;}"
        ".refresh-text{display:none;}"
        ".refresh-btn{background:transparent;border:none;color:var(--text-2);padding:0;"
        "width:36px;height:36px;border-radius:50%;display:flex;align-items:center;"
        "justify-content:center;font-size:16px;flex-shrink:0;}"
        ".refresh-btn:hover{background:var(--border);color:var(--text-1);}"
        ".header-actions{background:var(--bg-s1);border:1px solid var(--border);border-radius:20px;"
        "padding:2px;gap:2px;"
        "height:44px;}"
        ".next-pending-btn{min-height:44px;border-radius:18px;}"
        ".notif-btn{border-radius:50%;}"
        ".sidebar{display:none!important;}"
        ".app-body{flex-direction:column;height:calc(100vh - 48px - 68px);}"
        ".main-content{flex:1;height:100%;}"
        ".quick-add-bar{display:none;}"
        ".qa-fab{display:flex;bottom:88px;}"
        "}"
        # Bottom navigation bar (Todoist floating pill style)
        ".bottom-nav{display:flex;position:fixed;bottom:20px;left:16px;right:auto;"
        "background:var(--bg-s1);border:1px solid var(--border-h);"
        "border-radius:100px;padding:0 8px;height:56px;"
        "box-shadow:0 4px 20px rgba(0,0,0,0.35),0 1px 6px rgba(0,0,0,0.2);"
        "z-index:999;justify-content:space-around;align-items:center;gap:8px;}"
        "@supports(padding-bottom:env(safe-area-inset-bottom)){"
        ".bottom-nav{bottom:calc(20px + env(safe-area-inset-bottom));}}"
        ".bottom-nav-item{display:flex;flex-direction:column;align-items:center;"
        "gap:3px;padding:8px 16px;cursor:pointer;color:rgba(255,255,255,0.55);"
        "font-size:10px;font-weight:600;text-decoration:none;border-radius:100px;"
        "-webkit-tap-highlight-color:transparent;transition:color .15s,background .15s;}"
        ".bottom-nav-item:hover{background:var(--border);color:rgba(255,255,255,0.8);}"
        ".bottom-nav-item.active{color:#fff;background:rgba(255,255,255,0.1);}"
        ".bottom-nav-item svg{width:20px;height:20px;}"
        ".bottom-nav-search{display:flex;position:fixed;bottom:20px;right:20px;width:56px;height:56px;"
        "border-radius:50%;border:none;"
        "background:var(--bg-s1);border:1px solid var(--border-h);"
        "color:rgba(255,255,255,0.55);cursor:pointer;"
        "align-items:center;justify-content:center;flex-shrink:0;"
        "box-shadow:0 4px 20px rgba(0,0,0,0.35),0 1px 6px rgba(0,0,0,0.2);"
        "z-index:999;-webkit-tap-highlight-color:transparent;"
        "touch-action:manipulation;transition:color .15s,background .15s;}"
        "@supports(padding-bottom:env(safe-area-inset-bottom)){"
        ".bottom-nav-search{bottom:calc(20px + env(safe-area-inset-bottom));}}"
        ".bottom-nav-search:active{background:var(--border-h);color:#fff;}"
        ".bottom-nav-search svg{width:24px;height:24px;}"
        "@media(prefers-color-scheme:light){"
        ".bottom-nav{background:#fff;box-shadow:0 4px 20px rgba(0,0,0,0.12),0 1px 6px rgba(0,0,0,0.08);}"
        ".bottom-nav-item{color:rgba(0,0,0,0.45);}"
        ".bottom-nav-item:hover{color:rgba(0,0,0,0.7);}"
        ".bottom-nav-item.active{color:#000;background:rgba(0,0,0,0.06);}"
        ".bottom-nav-search{background:#fff;border-color:rgba(0,0,0,0.08);"
        "color:rgba(0,0,0,0.45);"
        "box-shadow:0 4px 20px rgba(0,0,0,0.12),0 1px 6px rgba(0,0,0,0.08);}"
        ".bottom-nav-search:active{background:rgba(0,0,0,0.06);color:#000;}}"
        # Search overlay
        ".search-overlay{display:none;position:fixed;top:0;left:0;right:0;"
        "bottom:calc(76px + env(safe-area-inset-bottom));z-index:10000;"
        "background:var(--bg-base);flex-direction:column;}"
        ".search-overlay.open{display:flex;}"
        ".search-header{display:flex;align-items:center;gap:10px;padding:12px 16px;"
        "border-bottom:1px solid var(--border);}"
        ".search-back{background:none;border:none;color:var(--text-2);cursor:pointer;"
        "width:36px;height:36px;border-radius:50%;display:flex;align-items:center;"
        "justify-content:center;flex-shrink:0;}"
        ".search-back:hover{background:var(--border);color:var(--text-1);}"
        ".search-input{flex:1;font-family:inherit;font-size:16px;background:var(--bg-s2);"
        "border:1px solid var(--border-h);border-radius:10px;padding:10px 14px;"
        "color:var(--text-1);outline:none;}"
        ".search-input:focus{border-color:rgba(99,102,241,0.5);}"
        ".search-input::placeholder{color:var(--text-3);}"
        ".search-results{flex:1;overflow-y:auto;padding:8px 16px;"
        "-webkit-overflow-scrolling:touch;}"
        ".search-empty{text-align:center;color:var(--text-3);padding:40px 20px;font-size:14px;}"
        ".search-section-label{font-size:11px;font-weight:700;color:var(--text-2);"
        "text-transform:uppercase;letter-spacing:.5px;padding:12px 0 6px;}"
        ".search-item{display:flex;align-items:flex-start;gap:12px;"
        "background:var(--bg-s1);border:1px solid var(--border);border-radius:8px;"
        "padding:14px 16px;margin-bottom:10px;cursor:pointer;"
        "transition:border-color .15s,background .15s;}"
        ".search-item:hover{border-color:var(--border-h);background:var(--bg-s2);}"
        ".search-item:active{background:var(--border);}"
        ".search-item-icon{width:32px;height:32px;border-radius:8px;flex-shrink:0;"
        "display:flex;align-items:center;justify-content:center;}"
        ".search-item-icon.task{background:var(--accent-bg);color:var(--accent-l);}"
        ".search-item-icon.event{background:var(--ok-bg);color:var(--ok);}"
        ".search-item-body{flex:1;min-width:0;}"
        ".search-item-title{font-size:14px;font-weight:500;color:var(--text-1);"
        "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        ".search-item-meta{font-size:12px;color:var(--text-2);margin-top:2px;"
        "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        ".search-type-badge{display:inline-block;font-size:10px;font-weight:700;"
        "text-transform:uppercase;letter-spacing:.5px;padding:2px 6px;"
        "border-radius:4px;margin-right:6px;vertical-align:middle;}"
        ".search-type-badge.task{background:var(--accent-bg);color:var(--accent-l);}"
        ".search-type-badge.event{background:var(--ok-bg);color:var(--ok);}"
        "::-webkit-scrollbar{width:6px;}"
        "::-webkit-scrollbar-track{background:transparent;}"
        "::-webkit-scrollbar-thumb{background:var(--scrollbar);border-radius:3px;}"
        # Splash screen styles
        "#splash{position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;"
        "background:#1a1a1a;display:flex;flex-direction:column;align-items:center;justify-content:center;"
        "transition:opacity .4s ease-out;}"
        "@media(prefers-color-scheme:light){#splash{background:#eeeef0;}}"
        "#splash.hide{opacity:0;pointer-events:none;}"
        "#splash .splash-dot{width:6px;height:6px;border-radius:50%;background:#6366f1;"
        "animation:pulse 1.2s ease-in-out infinite;}"
        "@keyframes pulse{0%,100%{opacity:.3;transform:scale(.8);}50%{opacity:1;transform:scale(1.2);}}"
        "</style>"
        "</head><body>"
        # Splash screen – covers white flash while app loads
        '<div id="splash"><img class="splash-logo" src="data:image/png;base64,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" width="80" height="80" alt="ActionOS" style="border-radius:18px;margin-bottom:20px;">'
        '<div class="splash-dot"></div></div>'
        # Header
        '<div class="header">'
        f'<a class="header-title-link" href="{function_url.rstrip("/")}?action=web" '
        f'onclick="goHome(event)"><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAIAAADdvvtQAAAAAXNSR0IArs4c6QAAAHJlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAABJKGAAcAAAAiAAAAUKABAAMAAAABAAEAAKACAAQAAAABAAAAwKADAAQAAAABAAAAwAAAAABBU0NJSQAAAE5RUkJWUFczNjQySEJLSTZNWUpESktDQUVFOX9x+gAAAj9pVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IlhNUCBDb3JlIDYuMC4wIj4KICAgPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4KICAgICAgPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIKICAgICAgICAgICAgeG1sbnM6ZGM9Imh0dHA6Ly9wdXJsLm9yZy9kYy9lbGVtZW50cy8xLjEvIgogICAgICAgICAgICB4bWxuczpleGlmPSJodHRwOi8vbnMuYWRvYmUuY29tL2V4aWYvMS4wLyI+CiAgICAgICAgIDxkYzpjcmVhdG9yPgogICAgICAgICAgICA8cmRmOlNlcT4KICAgICAgICAgICAgICAgPHJkZjpsaT5OUVJCVlBXMzY0MkhCS0k2TVlKREpLQ0FFRTwvcmRmOmxpPgogICAgICAgICAgICA8L3JkZjpTZXE+CiAgICAgICAgIDwvZGM6Y3JlYXRvcj4KICAgICAgICAgPGV4aWY6VXNlckNvbW1lbnQ+TlFSQlZQVzM2NDJIQktJNk1ZSkRKS0NBRUU8L2V4aWY6VXNlckNvbW1lbnQ+CiAgICAgIDwvcmRmOkRlc2NyaXB0aW9uPgogICA8L3JkZjpSREY+CjwveDp4bXBtZXRhPgqCG8eJAAAjx0lEQVR4Ae2dCXQcxZnHNaN7dIxuyZZsWT7wfeKLJARjOwQDeS8hhg1ZeOFBIFkgJFwv7IYku7zdzdvN6Q3LYUMIJISbbBJu8BEI2AbM4fuQLdtItg7rmNGMZkbHzP66WxqNdYz6qh7H0/NA7ump+ur7/vWvr6qrvqp2VNdMS7E/NgJ6EXDqzWjnsxGQELAJZPPAEAI2gQzBZ2e2CWRzwBACNoEMwWdntglkc8AQAjaBDMFnZ7YJZHPAEAI2gQzBZ2e2CWRzwBACNoEMwWdntglkc8AQAjaBDMFnZ7YJZHPAEAI2gQzBZ2e2CWRzwBACNoEMwWdntglkc8AQAjaBDMFnZ7YJZHPAEAI2gQzBZ2e2CWRzwBACNoEMwWdntglkc8AQAjaBDMFnZ7YJZHPAEAI2gQzBZ2e2CWRzwBACNoEMwWdntglkc8AQAmmGcpuROSJ9EMT/DodDkjjwVfref8uMglTKkPWRFDrj9ZGwsR6fITAmkkDhcAQIMjLSc7KzclxZmZnpqampYBIOh7t7egLBkK8rGAiE+OpwOBVuDdHe3K+KPllZGTmubFc26qCP5KH7+sKhnp6uQMjvR6lu+O10ykw3t/jTpVFKJBJ2Op0uV1auKzs7C3XSUp1Obvf19QVD6BP0dwW7u3us0ed07Qa/JYZAtHIIUeDOLS0uyM91Ac1AS1KaPvpJNQRSVFtru6e1zdvd0yuu2qAOXCkpzi8tcufmZKelpSoKyH6xXxmue3v7fP7AqTZPW0cnrBKpT5h2VVxYWFzohsq0K7nGTgMHDHt6ejt9Xc2tHR6vH/UGMJTTWvXHYf0JZXgUKqlqfBncwWbamdxnjWwxCfjQ7k80nmo51UH74+vISXXdlRp6SqTInVc5rjQ3JwsZkCmOJIU0Pn+w/mRze4fPdM8oNy0H7Wp8RUlWZkZMfzqCUiCBbyZNh9dXf6LF5+/CY42QTuSt1ILCYpHyT5Mt1UwkMq68ZEp1ZY4rMz460ZwkwyUUFeS7XJmdvgBuySwOIRnEq6vKq6sqMtLTZH2ixY58IfcsKZm4hyJ3WnpqZ2cXuUzUJyM9fcqk8bAHj4jkkZWIuaukwUvhq7jGQVo8LLKUQBhePaFiwvgymo4KcGJwkogXcWVnufNzvJ1ddGfG6wyB8HJqTRXNXamG08qL+0Wp2PzcHAYoHo9PHqUZ9Yt4PngwfeqE/LwcBMYtf+iPgIlrLHTnpaaleqXuzLqPdQSikmjo48qLtaITBQMJjAzceTmeTh/DESMcggEMSKfVVAG6EX3gNP+1d3RS4UYYhGnZWRnTp0xEmgF9UuA0dtGjGQEnCriaC4sIBChQZ8L40vgjjDE1VjhEu29r947t3+OIi0RqJo6jG9JdW4psqeKzpecjOGSkzuiwpk2uYmhoXJ/8PFdvXx+DayP6xEFuyE9WjLlAGWdfNa6M4fKQ4nV8BWLaGWNe3VxEQkmRu7SkwGBtKcojpKykAIG6pWFIZUUpRumWEAsj0oAawIE99r6gaysIhHevGlfKgMMsgwC6vLSQ9qoHo0gKDgP+STOXJn2oKQSmp6frECm3rmzMMYU9ikFAXTW+9CzxQDQIRr5M+ZgIEDAxNVJRVqSDAOFImFEz83J6yDdKeYhCYGmxO6Jx8KvIw5CBmZ5RCtB4G6iZIpEH4zoora0w8R7IkVJWXGB6awCjQneuMlOiyWKqqqRI82PXmEXAIXoxrTwgV1ZWJoaY27rQFsAhtKGB/Zg2ywnEEgjfzpRJXq5LX9OMb0JaWhqOTZMjITEdH887mnLFV0P5FYGMprX2quQqyMvBEDVFaErD9CweCPBFD4REEyjCIhdjDjGeNMLAU5Nvo8Jgs6DpWqfDKTUVLTWG8lQzk1yayKEmMVqkp6WxyKhJHzWSh6QRSyCgwQZNdTxEvzhfwQhfoqx3xkl22k8OB/qIqDC5FKm1aDIW5Vm71UK506yJ/wVN0EeYsf2FiyaQIzMzI76dun+lbeH801JT1TeyVIeDqUhBFYZY1kPUhw1I+qem4SfU668VKyIKjE1wjl2gWAKxZCF7CPNdtGIZ8/dOOeJibEPlFA6nU5vHUil3IBmDaIoY+Db2v04puZEZ7PhFEGJAk4mfxuivGqzVV5Qml66jCBak1eeSlq/VpxafUjg4oukj+nVPeB7iZsRVBM5f0wMwk1J9ZsyGj2aRFJmipYMMo42W9KOVO9p9Wf5oP5pzX7AHkoOeBHXDNF/YKRFUdTuDQL29vYKcEGJ7enspQm3NDOgvzA85COz8ex9EpwSCQbWAak8XIrCD8CDVGXFYgWC3esKpFiwndDgQThEqc6E2ymOCyvQ6kknGCv6I9UC0LeKaCQETYYUk3B/Q1IWhRqe/S1ijjMjCNdiK8pggyAMBuzjhUSOFE4ioeOKaRWDE6EFr4AtqEOcgxaNFATDpgl4UsXIQhRZIHQ5MEDEMwlJgZw+ACORjMdNibWw+1dc0MqLiTTcDgf6ugNYWRq5QqKfDQyyzyYYTm+zx+BGuejwmIcikEYHMGCICn9Z2r1b3rLpWBxOajOOg4IErkGVPRTBkclMA8caWdh2dIxXcfIqMakcqA3aM8S+aNLa0aWKPIhFNmlrazSUQ0oLB7tY22q3w+hVegOzbe040tpqIEZNv3k5/W5tHx6oWahCZ39LaoSPvaCRCVEurR6s7VKSRlwaGOSbOKGLjiaZTPILpIPRoNo52XziBKFjGt6Otw2tKnYEOD8vHGpri7QYazVz5PrA2NLawMU/9skMceQhBVMPJFt21RYjSsfomjDKljQEyUJvbQuKZH+c3E39inHj0+EmpzsyYuT9W3+jz6R83UE8MeI8cO9ljeIcQohCCqG6ml/QyiIx4L4wyDjjwAjJQixiYj6ieRUH1YERnz44cd34uW5/0mYcQPgDNoMEgEZETCnXzhMiuDN1+ESEYdbiugV0iuoUotYIoNisyLVrgzuN6xKoa8yY6MPFz6Eh9sLvHFOc6ZokksIhAlAQutHuP18eeCvbBa+UQjKG2jn560jh7FFzQh6dcvz9IRI4UsaRxSYHaCnV319Y18BxukD1RfRicMXBBH1Z8NaojjRO8Pn/tkXo4ZLB1Kfqo/GsdgVCIOmM/Fz00a5qEqrBWrKbayCWh09lVe7Sh3dNpSm1F64xN08jk2AJoDe5qqk2pHh6S0YfjDczVh74MS2lhBFmrrEIU4HG9sbmt7vhJdstbyR6pTq3fG89aEYuORH8STE44sBzQKREplkyQRiEcN5kmwetwpAGjZhGeWSmXKHT0IaRQjmseQR9FIXoZtjPzxM5kkqKhympWn0w201lSlM9WDTlCrX+P8xB8FIRY2mv3+BqbW6VnQIu5I5uUAAIpUAIHTKKdERTMXjguYJKCAL/QW7FIBCh0EJ2sV/T1mdjQR6xLFkFhLRVWkJ8DjQjXJ1ZN4TE1yjQPMyusVMAbf1cIDUVXFk4FKtPMYDZ/iW6mX+vXR14Spqvi4R98AqFuyK38NKJpQm8mjECDNJIPJwAdwvOUaC+wg0AsNEoTqfRfegeVOoCTaC3rI0U68pEnrNEDAtH5Kj9ZWVXSVIV8AoSsDo1ImnaRlOF/ORQEZazUZzik5u8HGF5GnDtR+3EAob6YpWMZFdFeZ7hiUX0kBvcOrgEr92WlhmcSeEdqPHL7YbKAWJFoSYnSJ6pA9CLBBIrqwYX11RNb+vDrM0ofZQQ2XMmE37FiJjrhRtoKiEPAJpA4bJNCsk2gpKhmcUbaBBKHbVJItgmUFNUszkibQOKwTQrJNoGSoprFGWkTSBy2SSHZJlBSVLM4I20CicM2KSTbBEqKahZn5Bm0FiYvhGOpFFZxJqxDyfpIG93PMH0kbM4EfBRSJphAVFJPDyvNfampaVKga2Ym68+EdQaJvunuBibOziWqQlwDGiKZABL04S/lok9GBmGBke5QN/vauE90APetjBEAGcolpiMjI0PWJx3diOYGHxm0VPRJLJkSRiDiJbq7Q263e9nSxcuXLZs7dzavGMnLySGsLhQKtZxqra09/N77O7a/9/6nn9YTFMTJYkMq29yvhPZRVeVlZecuXrR86ZKZM6eXl5W6XC7CcboCgaam5n37D27b/v6OHR82NTdTbXIgpbkqnCaN9kPrmjChatnSJUuXnDtt6pSSkmKaGMFJPr//RMPJXXv2bt26/ZOduzweT0ZmphK6dJoIS74kIKAMXILBUEVF2ZVXfPWrl395xvRzUhxRHxM9G0WKX+DT1npq46Ytjz3++x0ffkSdifBGcpsOnXPO1Ku/ftVll66prJqgFC3/VfTpV4Y7DfWf/uXFl3//xJOHao9wep8IbyR5nd7epYvPvebqr69auaKouGRAn6Hg8O65AwcOPfv8C88++3xjcwv0st4bWU0g0OFMqLVf/cptt91aXT1JgibSSysfwGjYv1IMXmp3KPjU08/+/Jfrmptb6OaGJdJ/A6+TnZV14w3X3XDDdbzfjdeFpYQH48hGkOuE6872ttaH1j+84ZFHaQl4oxGS6b1FXzmuvPyO22+98oq1GZkckdnHC8xGFSaNhqQ+5NjRup/9Yt0Lf/wThBbRxkZVwMptPSjBnoHcnJyf/Oe9d955R0GBOyUMdUZHR9FaiukME+w6f8HCi1ZfuGfvvrqjx+hA4pik/if6yuqJEx+4f91VV13F6dGyPqNTOUafbJfrc587f/GiBfSwra1tZnVngUDwM8uXPrz+/hUrLpQGfpG+eE2rX58w+BQUFl2yZk3l+Ip33t2GUSL84mioWreth0FGYYH7oQd+fcmll8peZyzqDFE5Ei4qLr1kzUWHDh3av/+gcQ4B9IwZ0x97dP38+QtSwj1jV1WsPjKtJ1bXrFzx+Xe3bm9qajLOIdhz8RdXr3/wf8eNr5T00fSR2mFkztx5C+bN2bhxM4M2yzhkEYEYZ2RlZT10/7rPX7BCMzpRKCPhzGzX6pUXfrJz5+EjdUbqjJ6reuKEx3+7YfKUqUb0KSwuveD8z2zctLm9vcNI38FT1QXnf/ahB+7Ld8uOOWqypotIuHrS5NmzZ7zy6uvSSX5yMLUmAToSW0Qgnin+7cc/+PKXv6K/thTj4FCW6zPnLX3t9Td5+tDXzgjgZ/z70AP/Q4s1rk9hUcnsmdP//OLLPFfqqzMqu6qq8tFHHiwpLZe6USOfSHhSzRTeyffGm5uMEFq9ClYQiIHhmotW/+iHP3A4NHZbI9rBWyDcReMqSv/y4isQSEedMfK95eZvfe1rVxllj6JeJDxh4qRQMPD2397RN6CGeT/7r39fvGSpOfqkRObNn79nz979+w8YcdIjYj/8pvClDA6dzMvNveuO7zlT07SNM4YrG70T6b30kktWr7qQ3enReyovaO7Tpk7+9o3flIaoZn0ifd+68fpzpk1FuFaRDMVWrfz8pcq4UGvmEdNL+8hS77rju/n5+t/mOaLgEW8KJxCbzxn5zpoz16TmJVvB3j9n6g3XX8t03ohWxbnJk+A3rvm6u6Bo7AfAOFKG/BQJI/Caq69iaDXkl/hfmRLDaX3rm9dhjmmtiyLDPbNmz734i1/Q0cDiKzz8V+EE4jCXK9dePrxgo3civcuWL2X+WlOdMZZnfvlLl10izfeY/Al/6dI1TGRThHrBeKy5c2ZjiPRYavbnyisuB3yzpQ6VJ5ZAAFQzqXrhwvlm9heKCVLbzVq9ckXsfs2hxg37DtsWL15UIT0nm9d/KaWE+8ZVViFcE6FRfuXKC9LSs8x0P/349J27cEFNzSQdveow2OLdEE6gBQvmuXLyzewvYsxhnUhTI2MhafmyJayvx8gw8dKBcIpQLxHlWXdTn15Dykg4Oyd/wby5mhqYBvkDScUSiLMBZs6YPlCW6f+GcW/MaKvvNaiwGTPOMV2PqECMVU9o1C5wuydNqhbQn/ZrNGvWDIZZUfVEXIglEG9jmlBVKUJvWWaExXx3vls6wkLFByiZzKwoL1eRVmeSsrLSzEy1LwlEbdjP7DyTyDrLGyvb+PHj9E2VjSV48HexBOJ8lNzc3MHSzL2KRIiSyVH9gnQIRHpXdrawCou4XNlMUaps9CQjXCQ9PcP8AdAAzvl5eaLDPMQSaMAQcf9SC9qar9b02lSXdNGmjzb5GlOLNVZWRiyBmGP1dnZqtFp1cmIXu3u6urpUTkaTjFg+FhrFDaIDgQAqqdfH7+9ikUc5AUi12RoS+nw+4mc0ZNCeVCyBOEL7xImT2rVSmcPR0eHp8HhVHmEmEyhIRJFK6TqSNTY1syyqkkCo7fGyoOcRRuiU+oYTKgeIOoxVsoglEFDu3btft3JjZXQePXZM05Iq0db79h8YS6z+3/cfOEgRKvMzvKUBEN4k7r2R+/YdUNm6VOo8PJlYArHU8PHOnQG/N0XMWz8IUlZfYRjPiJIswoYpEYRrGrSiPCFpw2vFhDsOZ5ff+/EnO0Wvp4olENrX1R3b8eHHMVHPJoAjieDI6Z7Qps1/1bQcxsLTBx98eLKhPkWKTDX140xtPNGAcE0L8ij/5qYtPd1B84dBjtSPPvoE9/b3TSCqiEb27HN/NLWuZGGOtO3btu/avUcTQPQa7Kl48aVXBfQaTsJLmppbNM27wLZdu/a8hxOSQ5vNRemZ517Q5J71lS7WA6ETe6teee2NfXt3pzjNW9hzOCLhvoce/g0LTypHrFF0qLPfPfGkp6PNzF6Vt811tD32uyd0BNqy1LDh4d9ijplOyJm+d/eul195nZ1tUcMFXQgnEC3S6/X+9Oe/4rBl0zBypL300ksbN72lY4cGHuvAwUPrNzxiZq/qSH1w/cNs9NHkDpUapYG9sXHTy6+8bJoTImyvrxfAO30+C144Z0VEolJnpcVFCxYuMmFV1ZneUH/85u/cBkCa+otoE2QX7Ecff7J08UIiCU3RZ+u77/zgh/fKR6JrXqbFgzLd99HHOy+5eDWRlqbo8/jjjz+44VG2iUVNFndhBYHQHpjYvbBg3uzqmimGMHKmdXq9N938vZ27drMuoQ8XlGH6btv291ZdeAERzcb0Sa87cvjGb9/S2sbmHp0Dc5pBa2srEagXX3xRZla2QX3+umXznd+/B1Jq7dz1gWkdgagz9pjOnTOLnQM6H6Sd6Uy8fee7t2/c9FdpG5eBDwHn7Od6d+u28z93HjsrdNaZM/3I4drrb7yp9vAR3WxWjMBJ1x6uO3jw4KoLV2Rm5+jRhz0YzvS333rrpltuYwLamoh6lLeIQJREO+O9O6++/kZZafGcOfOkMeyYuwqjFJHROVx76KZbvrt5y9sG2ROts8ampk2btsyaMX1C9SRpfKZ+WY1ZAEfaO+/87dv/dGvt4cM6hmJRy6IXDMDZ77Zjx44lixexA05bG3OmMaR7+umnb7/zbo+3U8dYPqqG1gvrCIRmLM7jh1597Y3jx44RqlLAVmJpV3zc1Ue2NjvSunu6n3zyqdtu//6+AwfZiazVyNHS0+7Zz8Ve92AwMHvmzGxX7tg0kqnT3t7+61/f98Mf3UvPZdD3xOpGxR87dvyll1/NcWXPnDEzNT1TCn2LQ2u5XYEheP74X+/91br7eKbTMZCP1UHrtdV749GP7pmNPsQm/8MVa9eu/cr0c6bFPBBBJv4Dtv7RqHK4wu9+/4f3PtjBtJsIz0xgF4usbNXgMIPLLltTWTkhBkSF3INDYw5XePGlV574w1M8ykmH0civz4lJb8Ily5/EoZ67aOG137h65YVDDlc4DRwChVk8YUv8088839jYxPkv1ox7Yo1MAIGU4gn97A5Jx7vMnz/3vOXL5s6eVVk5juAhqiQUDMrHuxzZ/v4HA8e7OExs6LH2R6+pMzZslJeXnrtoEZGpM2ecU1FRni0FD6UEeONdc/PefQe2cd7MB5Yd78KxQOHo8S5Tp04pKy2BstCdIU7DiUYmUbdt2/7xJ/LxLhmZypuyouZYdpEwAikW4o2YDKTN4VoIF1TaNN0ce//4i4dm3k+E1xkNX6oHffhLueijsFbWJ8h9yM19EV5nNH1AhnJBCU0UfWR/SRML4adABn2s9zqx2iaYQLGqABMf7oBIYkFRtLL1ia2d0a41b8wbTZDx+2cIb6KG2PpEoYhzIXwpI07Z9k9nAQI2gc6CSkykCTaBEon+WVC2TaCzoBITaYJNoESifxaUbRPoLKjERJpgEyiR6J8FZdsEOgsqMZEm2ARKJPpnQdk2gc6CSkykCTaBEon+WVD2GbQWpqyk9mOa6NVUFr3ZVR4Jy4u7HHNExLyA0B/1BJL0iIksSzQ8g4onmEDKijdwEM6Sxhsx5FeDUXcc69HL/xwXJ+91GNRX5BUVRFAQgUHpGRkFHFzldkdf98Qmdq/HS2Ak8X58LKs/6WgE6dhepxTUwq5pp1N6dYgMDvCAHppYpsyI2CeMQBJ1UlKyMzMK8nPz83KyszKoGM4NR0t+AZ1Qd4/PH+jw+vhLWIxoB8B5zSgwf97clStXcPTi5Brp8DzlvDr2d3Z0dLBHe9t7H7CZeteu3ZDMlDjoEatEuUnjgTLuXBf45OaAExTCD0r44BuhOSFBns4uj9cfCIW4mygaJSAeCN7wxidAGVdWXODOpdpkzki8iQKqwMFfehF/V7Cppf1Um5fDYkScNQEbKJpjy6+/7trzli9Nz1BirjkrU2r9kkpStfGfNF7s7Qm+8+72hx95dPOWt/gqKy8lMfGDY6HPLCnKLy8tJDhaBkFSYwg+MpccKN/u8TU2t9HMpI7WRD3UibKaQKBAS6qsKAUdWpjUSY31AUE+nk7/8fomn7/LXFdEO66unnDPv3xfOjyaCP/4Ly9DVeqIfeyRvj/9+cX/+Ml/Hz9eTxzlWBZo+B1AcnNc1VXleGWw4jNmZgDBQze2tJ1oPIXnBqsxs5iYwNJdGfheuqppk6tKigqwQQ06iqmkJGNxobu3t8/nV3uC05gw8YalCz7/2Uc2PLiE91Rw9LjKlx+wG8mRMmPGLI6C379//+HDdWZtowGfspLCqTVV2dkZXI+pfxQcSOPOy83LcXX6uogQtpJD1hEIz8wRlNOnTsx1ZatxPEPgoynS1AoL8vrCfZ2+gHGM5PdzrXrowftKpXfkqD0ValAr+fUGay7+wsGD5ry/DMaMKy+qmci5qtJm58GC1F2RBV/ozs/1dvoZIRnHR12xVm0sxLzM9DTYA4fUt60RbShw5zGqlbp8A76aIfPyZUs3rL8/P9/Q+7nYibxq5Qp2A7Kfy8h4SPY9BbBHB3WiKJE3Iz2Nvq+9o9OyvswiD0RlT5lUiW0G2QNYiEKOt7MLGunjECOGkpKSRx9+sGLceOPv58rMylm2ZNGLL7/m9/v1jc+o+NycLHou5SE0SggdF3guXm/NUcNtHcLONj1dLStmoumwSosLigrydfRcp2srfQNunvcZZvKoMvxXNXd4cuFtSIbeVRhbTLinZvLUu26/lY4j9rb6ax6eqqsqMMqI+4kWB8hADeCmoB0VO9qFzjoYTdzw+1KbSE8fX15iCjqKfNwYTqi4SA8jOYaXTZ+8cdzMF+REeq+4Yu3SxYvYQTYcgfh3pPoucpvim6MFAfX4imJg1z6UispQe2EBgcLFRW726JlIIIxDmjwRoFl/Jpauu/aajExOUdE8UB0VVAYfmVnfuOYfddjIXEZFaaGOjKMqI4PDHk0aGMbGSWbKT5orQGupDAuKC7HEvNqSNUAgk2xMmUiT/ao/jH4mTqhi2Cu9j93kT9/qVSsQThHqBWMFE6oYIgIfZj30jcnU609KsQQCl+ysTJ68TAcI1RlBM82vyZGwTXjZsiVuTgVRMYGpCUcEugtLEE4R6jMCCyboexSIXwqSgT1bDPKxRQsnEC0MLx1bpFnXYIRwTY0Mb7V0yblmKTBcztLFi7U4RGlmCxNEtC50A/Zcl9pXBw23ReUdsQRCCWaQVaqiIxlLjKzgq+/DMjIzpk2doqMglVmmTZvMI7TKxKiN8pigMr2OZCaepTRa6YIJ5HDIC9rqq3g0PUe4T8OlkbGyprIXIz1DS2aAGGWOIM6EW5Hi4mJW6dV6FPRPc6K/2vSaNeStoJxcJnZpTCyB0N1JBQv7AI56+dSTNMkmHc0pikAsJlCEekLQhYkYAEXxliJAol/EXAisXUVh9WjqM1CTfCaQ5Ok1QahyQDPiNbBTk/I68BEtH5XEEogRpfxYK6jCpNAq6kwlsrR1lsB8fr8c3KMyk6ZkDoRThHqnopVwmrTBzL7ePk2Deo3ypeRiCURnEQppeKzVZAD1JMWf9qqNXiA9ZzOeOCnu/WUpvByNACOVBCIZYbsYoDK9JnCUxER1Cuuv+9URTSAH8YSCHCkDoGCwW9Nrtol43rV7r46aUJll9+69EEJlYpKxZh4ISif5ifgAuz8QFOZu+1UWSyDaFjbI4SkiIHIQ+6KJnRzzunXr9ki41/xnE+n9L73vbtuu6bx6lPf6hHSpcJIzQ2m94tybUqOiCZSCF6WaRbz1g7beIUnW0H45kpJ3sNXW1sYcLGwSsx2phw8f5sxUilAvEeU7PD5NTkulcHYhEZ0I+FrgUSn7tGRiCSQVFUlpafVo8hOnKTjKFx6ACSZXP+BQxFBhHo/3uef/T4Bjdzzz7Au8f1MToUnMcbTsPNE0nz4KJKfdBvDm1g5R8xUxRQknEDMdeCDTMeLhjq0IMYaoveS83Keeea7+02MpvB7ArI8zrf74UcRmZOgJsD/Z1KZpCXZMraEjjo0dP8Yj1MYua8wUxhPQGupPtEiPS8ZlyRIAqKmFjSxqX/gdWyxT142NzT/7xTr5pikaSUJ++vN1TU0t0rS4xg9OiPBc9i2Z5YTQBqjrT/Jyag0zUhq1HkxuRUgrGHFsODQiJN74tARAM/CsO87TuM7q55UJPItNqBo3m3e+GI+YcaY/88wzv1x3n+6thhKHfF15eS5WWoz39Xid4w1Nbe1esxg5SJaRrqwgEOUq7YzWT+idEYwAJRAI1dbV84iBzJEsUnFPyhf52ztbF86fM5F3TxnhEG9Yevut2+64m4GwkQojqokxL1tzNK2EDDcVHegQG05qe3XrcDnq71hEIBSivtkciJPPz3Xpcx6g0xUIHjpSz9yJwd4dUUwZv7lx86xZ0yfxDjwd3h76OtO3bNl88y23dXZ2GtmSoYDDfi48a36eSx+HJHVgT3PrsYYm/U1LPXEGUlpHIEqkT/bw1NrXxxY4mKS+OwMR0Gnr8NbWNdAbGmSPYrtMx8Arr76BU5y/YL6DMbV6V+RMZ9vzY799/K677+HVJwbZo+iDjUyYtXf4sjLTXRpfpwcgfX2R4w3N+B6ppQ7UrgX/WkogDMM6fDWbcmhnBCtSi/Fbv0Id5jPo1z890czTion4UDpdz+tvbNyzZ++UmknlFeOl+SG0HI3a8svLSLN71667//me9Rt+Q3dMv2xWPWEaBrIjh8h/ODTmhlfF61A6D7lHjjUo4x4r2UPRVu+NV7CWh0EOd34Oxyvk5bpAaoAW0QcHCQfQ7AqEWts9re1eMJXZpggw+S/zSXl5uWsuvuiKtZcvWjg/Jzd/xAL8Pu+Ojz5+7rk/8s48XkXN63NGTGb8JovEnMZRXFRAODmRqQMcPQ0cMGQg6PV1tbR2eDt9cH4AQ+Pla5CQGAIpCgITbQhXlOPKosERS0O/xtkFhER09/QGgiFfV4AhM18tOCSI+mBUxDxyzaRJvMJs1szpVVWVvL8MInd28n6uE3v27v9k5666uqNEPTPfY0o3GqeiIAR7KmgzxDUTmYq3JjSPr9ymXbFEzRoRKxW0K1KKViaOnokkkKIWNSf3GDSv/iY08FX63n8rjgVm/0SnxgedGHZxpBPiWfKkLtGEsY4pwx1NKsv4KL6nH4wBfKSv1uMzRHnzZmOHCFb9FQjkUd9g3z3kq2pJ5iQczhItq1vm6BArRcZnEBx+Siw+sbpxrXnmdEh++2uSI2ATKMkJYNR8m0BGEUzy/DaBkpwARs23CWQUwSTPbxMoyQlg1HybQEYRTPL8NoGSnABGzbcJZBTBJM9vEyjJCWDUfJtARhFM8vw2gZKcAEbNtwlkFMEkz28TKMkJYNR8m0BGEUzy/DaBkpwARs23CWQUwSTPbxMoyQlg1HybQEYRTPL8NoGSnABGzbcJZBTBJM9vEyjJCWDUfJtARhFM8vw2gZKcAEbNtwlkFMEkz28TKMkJYNR8m0BGEUzy/DaBkpwARs23CWQUwSTPbxMoyQlg1Pz/BwmAmGbhpSkgAAAAAElFTkSuQmCC" width="28" height="28" alt="ActionOS" style="border-radius:7px;display:block;"></a>'
        # Mobile section picker (hidden on desktop)
        + f'<button class="section-picker" id="section-picker" onclick="toggleSectionPicker()">'
        f'<span class="section-picker-label" id="section-picker-label">{first_label}</span>'
        f'<span class="badge" id="section-picker-badge">{first_badge}</span>'
        f'<span class="section-picker-chevron">&#9660;</span>'
        f"</button>" + '<div class="header-actions">'
        '<button class="next-pending-btn" id="shell-next-btn" onclick="nextPendingInShell()">&#8595; Next <span id="shell-next-label"></span></button>'
        '<button class="refresh-btn" onclick="refreshActive()">&#8635;<span class="refresh-text"> Refresh</span></button>'
        '<button class="notif-btn" id="notif-btn" onclick="requestNotifPermission()" title="Enable notifications" style="display:none">'
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>'
        '<path d="M13.73 21a2 2 0 0 1-3.46 0"/>'
        "</svg></button>"
        "</div></div>"
        # Quick-add bar
        '<div class="quick-add-bar">'
        '<input type="text" id="qa-input" class="quick-add-input" placeholder="Add new action..." '
        "onkeydown=\"if(event.key==='Enter')doQuickAdd()\">"
        f'<select id="qa-project" class="quick-add-select">{project_options_html}</select>'
        '<input type="date" id="qa-date" class="quick-add-select">'
        '<select id="qa-priority" class="quick-add-select">'
        '<option value="">Priority</option>'
        '<option value="4">P1</option>'
        '<option value="3">P2</option>'
        '<option value="2">P3</option>'
        '<option value="1">P4</option>'
        "</select>"
        '<button class="quick-add-btn" id="qa-btn" onclick="doQuickAdd()">+ Add</button>'
        "</div>"
        # App body: sidebar + main content
        '<div class="app-body">'
        '<div class="sidebar" id="sidebar">' + sidebar_tabs_html + "</div>"
        '<div class="main-content">' + iframes_html + "</div>"
        "</div>"
        # Backdrop and section dropdown
        + '<div class="section-dropdown-backdrop" id="section-dropdown-backdrop" '
        'onclick="closeSectionPicker()"></div>'
        + '<div class="section-dropdown" id="section-dropdown">'
        '<div class="section-dd-header">'
        '<span class="section-dd-title">Sections</span>'
        '<button class="section-dd-edit-btn" id="section-dd-edit-btn" onclick="toggleEditMode()">Edit</button>'
        "</div>" + dropdown_items_html + "</div>"
        # Mobile FAB + bottom sheet (Todoist-style with SVG icons)
        '<a class="cal-fab" id="cal-fab" href="x-fantastical3://add">'
        '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="4" width="18" height="18" rx="2"/>'
        '<line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>'
        '<line x1="3" y1="10" x2="21" y2="10"/>'
        '<line x1="12" y1="14" x2="12" y2="18"/><line x1="10" y1="16" x2="14" y2="16"/>'
        "</svg></a>"
        '<button class="qa-fab" id="qa-fab" onclick="window.location.href=\'todoist://addtask\'">'
        '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">'
        '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>'
        "</svg></button>"
        '<div class="qa-sheet-overlay" id="qa-sheet-overlay" onclick="closeMobileSheet()"></div>'
        '<div class="qa-sheet" id="qa-sheet">'
        '<div class="qa-sheet-handle"></div>'
        '<input type="search" id="qa-m-input" class="qa-sheet-task" placeholder="Enter Task" '
        'autocomplete="off" autocorrect="off" autocapitalize="sentences" '
        "oninput=\"var s=document.getElementById('qa-m-send');var hasText=this.value.trim().length>0;s.disabled=!hasText;s.style.opacity=hasText?'1':'.35';\" "
        "onkeydown=\"if(event.key==='Enter'&&!event.shiftKey)doMobileQuickAdd()\">"
        '<textarea id="qa-m-desc" class="qa-sheet-desc" placeholder="Description" rows="1" '
        'tabindex="-1" '
        'oninput="autoResize(this)"></textarea>'
        '<div class="qa-sheet-icons">'
        # Calendar icon - label wraps hidden date input for native picker
        '<label class="qa-icon-btn" id="qa-m-date-btn" for="qa-m-date" title="Due date">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
        '<rect x="3" y="4" width="18" height="18" rx="2"/>'
        '<line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>'
        '<line x1="3" y1="10" x2="21" y2="10"/>'
        "</svg></label>"
        '<input type="date" id="qa-m-date" style="position:absolute;opacity:0;width:0;height:0" '
        'onchange="onMDateChange()">'
        # Bell icon (decorative)
        '<button class="qa-icon-btn" type="button" title="Reminder">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
        '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>'
        '<path d="M13.73 21a2 2 0 0 1-3.46 0"/>'
        "</svg></button>"
        # Flag icon - priority (cycles P1-P4)
        '<button class="qa-icon-btn" id="qa-m-pri-btn" type="button" onclick="cycleMPriority()" title="Priority">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
        '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>'
        '<line x1="4" y1="22" x2="4" y2="15"/>'
        "</svg></button>"
        # Person icon (decorative)
        '<button class="qa-icon-btn" type="button" title="Assign">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
        '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
        '<circle cx="12" cy="7" r="4"/>'
        "</svg></button>"
        # Tag icon - cycles labels (none → Commit → Best Case)
        '<button class="qa-icon-btn" id="qa-m-label-btn" type="button" onclick="cycleMLabel()" title="Label">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
        '<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>'
        '<line x1="7" y1="7" x2="7.01" y2="7"/>'
        "</svg></button>"
        # More dots (decorative)
        '<button class="qa-icon-btn" type="button" title="More">'
        '<svg viewBox="0 0 24 24" fill="currentColor">'
        '<circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/>'
        "</svg></button>"
        "</div>"
        '<div class="qa-sheet-bottom">'
        '<div class="qa-sheet-inbox-area">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
        '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>'
        '<path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>'
        "</svg>"
        f'<select id="qa-m-project" class="qa-sheet-project">{project_options_html}</select>'
        "</div>"
        '<button class="qa-sheet-send" id="qa-m-send" type="button" onclick="doMobileQuickAdd()" disabled style="opacity:.35">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="12" y1="19" x2="12" y2="5"/>'
        '<polyline points="5 12 12 5 19 12"/>'
        "</svg></button>"
        "</div>"
        "</div>"
        # Bottom navigation bar (mobile, Todoist-style)
        '<nav class="bottom-nav" id="bottom-nav">'
        '<div class="bottom-nav-item" data-tab="home" onclick="switchTab(\'home\')">'
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>'
        "<span>Home</span></div>"
        '<div class="bottom-nav-item" data-tab="calendar" onclick="switchTab(\'calendar\')">'
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'
        "<span>Calendar</span></div>"
        '<div class="bottom-nav-item" data-tab="unread" onclick="switchTab(\'unread\')">'
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>'
        "<span>Unread</span></div>"
        '<div class="bottom-nav-item" data-tab="code" onclick="switchTab(\'code\')">'
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>'
        "<span>Code</span></div>"
        "</nav>"
        '<button class="bottom-nav-search" id="nav-search-btn" onclick="openSearch()">'
        '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
        "</button>"
        # Search overlay (full-screen)
        '<div class="search-overlay" id="search-overlay">'
        '<div class="search-header">'
        '<button class="search-back" onclick="closeSearch()">'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>'
        "</button>"
        '<input type="search" class="search-input" id="search-input" placeholder="Search actions &amp; calendar..." '
        'autocomplete="off" autocorrect="off" autocapitalize="off">'
        "</div>"
        '<div class="search-results" id="search-results">'
        '<div class="search-empty">Search across all your actions and calendar events</div>'
        "</div>"
        "</div>"
        # JavaScript
        "<script>"
        "var _resizeTimer;function autoResize(el){clearTimeout(_resizeTimer);_resizeTimer=setTimeout(function(){el.style.height='auto';el.style.height=el.scrollHeight+'px';},50);};"
        "var activeTab='" + tabs[0][0] + "';"
        "var tabIds=" + tab_ids_json + ";"
        "var tabUrls=" + tab_urls_json + ";"
        # Dismiss splash 400ms after DOM is ready — shell is visible, iframes load in-place
        "(function(){"
        "var splash=document.getElementById('splash');"
        "if(!splash)return;"
        "function dismiss(){splash.classList.add('hide');"
        "setTimeout(function(){splash.remove();},400);}"
        "if(document.readyState==='loading'){"
        "document.addEventListener('DOMContentLoaded',function(){setTimeout(dismiss,400);},{once:true});"
        "}else{setTimeout(dismiss,400);}"
        "})();"
        # srcdoc already provides dark background for lazy iframes
        # goHome: on mobile open section picker, on desktop reload
        "function goHome(e){"
        "e.preventDefault();"
        "if(window.innerWidth<=768){"
        "toggleSectionPicker();"
        "}else{"
        "window.location.reload();"
        "}"
        "}"
        # switchTab
        "function switchTab(tab){"
        "if(tab===activeTab){"
        "var f=document.getElementById('frame-'+tab);"
        "if(f&&f.contentWindow&&typeof f.contentWindow.closeDetailView==='function')f.contentWindow.closeDetailView();"
        "return;}"
        "activeTab=tab;"
        "tabIds.forEach(function(id){"
        "document.getElementById('tab-'+id).className='sidebar-tab'+(id===tab?' active':'');"
        "document.getElementById('frame-'+id).style.display=id===tab?'block':'none';"
        "});"
        "var frame=document.getElementById('frame-'+tab);"
        "if(frame&&(!frame.src||frame.src==='about:blank'||frame.hasAttribute('srcdoc'))){"
        "frame.removeAttribute('srcdoc');"
        "frame.src=tabUrls[tab];"
        "}"
        # Sync mobile picker label/badge
        "var sidebarTab=document.getElementById('tab-'+tab);"
        "if(sidebarTab){"
        "var lbl=sidebarTab.querySelector('.tab-label');"
        "var bdg=sidebarTab.querySelector('.badge');"
        "var pl=document.getElementById('section-picker-label');"
        "var pb=document.getElementById('section-picker-badge');"
        "if(pl&&lbl)pl.textContent=lbl.textContent;"
        "if(pb&&bdg)pb.textContent=bdg.textContent;"
        "}"
        # Sync active state in dropdown
        "document.querySelectorAll('.section-dropdown-item').forEach(function(item){"
        "var isActive=item.getAttribute('data-tab-id')===tab;"
        "item.classList.toggle('active',isActive);"
        "var ico=item.querySelector('.section-dropdown-icon');if(ico){ico.style.color=isActive?'var(--accent-l)':'var(--text-2)';}"
        "});"
        # Sync bottom nav active state
        "document.querySelectorAll('.bottom-nav-item').forEach(function(item){"
        "item.classList.toggle('active',item.getAttribute('data-tab')===tab);"
        "});"
        # Show calendar FAB only when calendar tab is active
        "var calFab=document.getElementById('cal-fab');"
        "if(calFab)calFab.style.display=tab==='calendar'?'flex':'none';"
        # Show Next button only when home tab is active
        "var nextBtn=document.getElementById('shell-next-btn');"
        "if(nextBtn)nextBtn.style.display=tab==='home'?'inline-flex':'none';"
        "}"
        # Section picker
        "function toggleSectionPicker(){"
        "var dd=document.getElementById('section-dropdown');"
        "var bd=document.getElementById('section-dropdown-backdrop');"
        "var isOpen=dd.classList.contains('open');"
        "dd.classList.toggle('open',!isOpen);"
        "bd.classList.toggle('open',!isOpen);"
        "}"
        "function closeSectionPicker(){"
        "document.getElementById('section-dropdown').classList.remove('open');"
        "document.getElementById('section-dropdown-backdrop').classList.remove('open');"
        "}"
        "function selectSection(tab){"
        "closeSectionPicker();"
        "switchTab(tab);"
        "}"
        "function refreshActive(){"
        "var frame=document.getElementById('frame-'+activeTab);"
        "if(frame){frame.contentWindow.location.reload();}"
        "}"
        # Next pending item in home iframe
        "function nextPendingInShell(){"
        "var frame=document.getElementById('frame-home');"
        "if(!frame||!frame.contentWindow)return;"
        "try{"
        "var cw=frame.contentWindow;"
        "var cards=cw._getPendingSections?cw._getPendingSections():[];"
        "var total=cards.length;"
        "if(!total)return;"
        "if(cw.nextPendingItem)cw.nextPendingItem();"
        "var idx=cw._pendingIdx||0;"
        "var pos=idx===0?total:idx;"
        "var lbl=document.getElementById('shell-next-label');"
        "if(lbl)lbl.textContent=pos+'/'+total;"
        "}catch(e){}}"
        # Quick-add task
        f"function doQuickAdd(){{"
        "var inp=document.getElementById('qa-input');"
        "var content=inp.value.trim();"
        "if(!content)return;"
        "var btn=document.getElementById('qa-btn');"
        "btn.disabled=true;btn.textContent='Adding...';"
        "var payload={content:content};"
        "var pid=document.getElementById('qa-project').value;"
        "var dt=document.getElementById('qa-date').value;"
        "var pri=document.getElementById('qa-priority').value;"
        "if(pid)payload.project_id=pid;"
        "if(dt)payload.due_date=dt;"
        "if(pri)payload.priority=parseInt(pri);"
        f'fetch("{function_url.rstrip("/")}?action=create_task",'
        "{"
        'method:"POST",'
        'headers:{"Content-Type":"application/json"},'
        "body:JSON.stringify(payload)"
        "})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "if(d.ok){"
        "inp.value='';"
        "btn.textContent='\\u2713 Added';"
        "setTimeout(function(){btn.textContent='+ Add';btn.disabled=false;},1500);"
        # Reload active Todoist iframe to show new task
        "var activeFrame=document.getElementById('frame-'+activeTab);"
        "if(activeFrame&&['inbox','commit','p1','bestcase'].indexOf(activeTab)!==-1){"
        "activeFrame.contentWindow.location.reload();}"
        "}else{"
        "btn.textContent='Failed';"
        "setTimeout(function(){btn.textContent='+ Add';btn.disabled=false;},1500);"
        "}"
        "}).catch(function(){btn.textContent='Failed';"
        "setTimeout(function(){btn.textContent='+ Add';btn.disabled=false;},1500);"
        "});}"
        # Mobile bottom sheet: open/close/reset
        "var _mPri='';"
        "var _mPriCycle=['','4','3','2','1'];"
        "var _mPriIdx=0;"
        "var _mLabel='';"
        "var _mLabelCycle=['','Commit','Best Case'];"
        "var _mLabelIdx=0;"
        "function openMobileSheet(){"
        "document.getElementById('qa-sheet-overlay').classList.add('open');"
        "document.getElementById('qa-sheet').classList.add('open');"
        "document.getElementById('qa-m-input').focus();"
        "}"
        "function closeMobileSheet(){"
        "document.getElementById('qa-sheet-overlay').classList.remove('open');"
        "document.getElementById('qa-sheet').classList.remove('open');"
        "}"
        "function resetMobileSheet(){"
        "document.getElementById('qa-m-input').value='';"
        "var descEl=document.getElementById('qa-m-desc');"
        "if(descEl){descEl.value='';descEl.style.height='';}"
        "document.getElementById('qa-m-date').value='';"
        "document.getElementById('qa-m-date-btn').classList.remove('active-date');"
        "_mPriIdx=0;_mPri='';"
        "var pb=document.getElementById('qa-m-pri-btn');"
        "pb.classList.remove('active-p1','active-p2','active-p3');"
        "var s=document.getElementById('qa-m-send');s.disabled=true;s.style.opacity='.35';"
        "_mLabelIdx=0;_mLabel='';"
        "var lb=document.getElementById('qa-m-label-btn');"
        "if(lb)lb.classList.remove('active-commit','active-bestcase');"
        "}"
        "function onMDateChange(){"
        "var dt=document.getElementById('qa-m-date').value;"
        "var btn=document.getElementById('qa-m-date-btn');"
        "if(dt){btn.classList.add('active-date');}"
        "else{btn.classList.remove('active-date');}"
        "}"
        "function cycleMPriority(){"
        "_mPriIdx=(_mPriIdx+1)%_mPriCycle.length;"
        "_mPri=_mPriCycle[_mPriIdx];"
        "var btn=document.getElementById('qa-m-pri-btn');"
        "btn.classList.remove('active-p1','active-p2','active-p3');"
        "if(_mPri==='4')btn.classList.add('active-p1');"
        "else if(_mPri==='3')btn.classList.add('active-p2');"
        "else if(_mPri==='2')btn.classList.add('active-p3');"
        "}"
        "function cycleMLabel(){"
        "_mLabelIdx=(_mLabelIdx+1)%_mLabelCycle.length;"
        "_mLabel=_mLabelCycle[_mLabelIdx];"
        "var btn=document.getElementById('qa-m-label-btn');"
        "btn.classList.remove('active-commit','active-bestcase');"
        "if(_mLabel==='Commit')btn.classList.add('active-commit');"
        "else if(_mLabel==='Best Case')btn.classList.add('active-bestcase');"
        "}"
        "function doMobileQuickAdd(){"
        "var content=document.getElementById('qa-m-input').value.trim();"
        "if(!content)return;"
        "var btn=document.getElementById('qa-m-send');"
        "btn.disabled=true;"
        "var payload={content:content};"
        "var descEl=document.getElementById('qa-m-desc');"
        "var desc=descEl?descEl.value.trim():'';"
        "var pid=document.getElementById('qa-m-project').value;"
        "var dt=document.getElementById('qa-m-date').value;"
        "if(desc)payload.description=desc;"
        "if(pid)payload.project_id=pid;"
        "if(dt)payload.due_date=dt;"
        "if(_mPri)payload.priority=parseInt(_mPri);"
        "if(_mLabel)payload.labels=[_mLabel];"
        f'fetch("{function_url.rstrip("/")}?action=create_task",'
        "{"
        'method:"POST",'
        'headers:{"Content-Type":"application/json"},'
        "body:JSON.stringify(payload)"
        "})"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "btn.disabled=false;"
        "if(d.ok){"
        "resetMobileSheet();"
        "closeMobileSheet();"
        "var activeFrame=document.getElementById('frame-'+activeTab);"
        "if(activeFrame&&['inbox','commit','p1','bestcase'].indexOf(activeTab)!==-1){"
        "activeFrame.contentWindow.location.reload();}"
        "}"
        "}).catch(function(){btn.disabled=false;});}"
        # Search functionality
        "var _searchTimer=null;"
        "function openSearch(){"
        "document.getElementById('search-overlay').classList.add('open');"
        "var inp=document.getElementById('search-input');"
        "inp.value='';inp.focus();"
        "document.getElementById('search-results').innerHTML="
        "'<div class=\"search-empty\">Search across all your actions and calendar events</div>';"
        "inp.addEventListener('input',_onSearchInput);"
        "}"
        "function closeSearch(){"
        "document.getElementById('search-overlay').classList.remove('open');"
        "clearTimeout(_searchTimer);"
        "}"
        "function _onSearchInput(e){"
        "clearTimeout(_searchTimer);"
        "var q=e.target.value.trim();"
        "if(!q){"
        "document.getElementById('search-results').innerHTML="
        "'<div class=\"search-empty\">Search across all your actions and calendar events</div>';"
        "return;}"
        "if(q.length<2)return;"
        "_searchTimer=setTimeout(function(){_doSearch(q);},300);"
        "}"
        "function _doSearch(q){"
        "document.getElementById('search-results').innerHTML="
        "'<div class=\"search-empty\">Searching...</div>';"
        f"fetch('{base}?action=search&q='+encodeURIComponent(q))"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "var html='';"
        "var items=[];"
        "if(d.tasks)d.tasks.forEach(function(t){items.push({type:'task',data:t});});"
        "if(d.events)d.events.forEach(function(ev){items.push({type:'event',data:ev});});"
        "items.forEach(function(item){"
        "if(item.type==='task'){"
        "var t=item.data;"
        "var pri=t.priority===4?'P1':t.priority===3?'P2':t.priority===2?'P3':'';"
        "var meta=[];"
        "if(t.project_name)meta.push(t.project_name);"
        "if(pri)meta.push(pri);"
        "if(t.due_date)meta.push(t.due_date);"
        "if(t.labels&&t.labels.length)meta.push(t.labels.join(', '));"
        "html+='<div class=\"search-item\" onclick=\"closeSearch();switchTab(\\'commit\\')\">'"
        '+\'<div class="search-item-icon task"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg></div>\''
        "+'<div class=\"search-item-body\">'"
        "+'<div class=\"search-item-title\"><span class=\"search-type-badge task\">Task</span>'+_esc(t.content)+'</div>'"
        "+(meta.length?'<div class=\"search-item-meta\">'+_esc(meta.join(' · '))+'</div>':'')+'</div></div>';"
        "}else{"
        "var ev=item.data;"
        "var meta=[];"
        "if(ev.start){"
        "var dt=ev.start.length>10?new Date(ev.start).toLocaleDateString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}):ev.start;"
        "meta.push(dt);}"
        "if(ev.location)meta.push(ev.location);"
        "if(ev.calendar_type)meta.push(ev.calendar_type);"
        "html+='<div class=\"search-item\" onclick=\"closeSearch();switchTab(\\'calendar\\')\">'"
        '+\'<div class="search-item-icon event"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></div>\''
        "+'<div class=\"search-item-body\">'"
        "+'<div class=\"search-item-title\"><span class=\"search-type-badge event\">Event</span>'+_esc(ev.title)+'</div>'"
        "+(meta.length?'<div class=\"search-item-meta\">'+_esc(meta.join(' · '))+'</div>':'')+'</div></div>';"
        "}"
        "});"
        "if(!html)html='<div class=\"search-empty\">No results found</div>';"
        "document.getElementById('search-results').innerHTML=html;"
        "}).catch(function(){"
        "document.getElementById('search-results').innerHTML='<div class=\"search-empty\">Search failed</div>';});"
        "}"
        "function _esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;}"
        # postMessage handler (badge counts + viewer open)
        "window.addEventListener('message',function(e){"
        "if(e.data&&e.data.type==='count'){"
        "var badge=document.getElementById('badge-'+e.data.source);"
        "if(badge){badge.textContent=e.data.count;}"
        "var dpBadge=document.getElementById('dpbadge-'+e.data.source);"
        "if(dpBadge){dpBadge.textContent=e.data.count;}"
        "if(e.data.source===activeTab){"
        "var pb=document.getElementById('section-picker-badge');"
        "if(pb)pb.textContent=e.data.count;"
        "}"
        # Seed the Next button label when home reports its count
        "if(e.data.source==='home'){"
        "var nl=document.getElementById('shell-next-label');"
        "if(nl&&!nl.textContent)nl.textContent='1/'+(e.data.count||'?');"
        "}"
        "}"
        "if(e.data&&(e.data.type==='markread'||e.data.type==='unstar'||e.data.type==='skip-inbox')){"
        # Reload starred frame when an email is actioned from the viewer
        "var sf=document.getElementById('frame-starred');"
        "if(sf&&sf.src&&!sf.hasAttribute('srcdoc'))sf.contentWindow.location.reload();"
        "}"
        "if(e.data&&e.data.type==='viewer-open'){closeSectionPicker();}"
        "if(e.data&&e.data.type==='switchTab'){switchTab(e.data.tab);}"
        "},{passive:true});"
        # Drag-and-drop tab reordering
        "function initDragDrop(){"
        "document.querySelectorAll('.sidebar-tab').forEach(function(tab){"
        "tab.addEventListener('dragstart',function(e){"
        "e.dataTransfer.setData('text/plain',tab.getAttribute('data-tab-id'));"
        "tab.classList.add('dragging');},{passive:true});"
        "tab.addEventListener('dragend',function(){"
        "tab.classList.remove('dragging');"
        "document.querySelectorAll('.sidebar-tab').forEach(function(t){"
        "t.classList.remove('drag-over');});},{passive:true});"
        "tab.addEventListener('dragover',function(e){"
        "e.preventDefault();tab.classList.add('drag-over');});"
        "tab.addEventListener('dragleave',function(){"
        "tab.classList.remove('drag-over');},{passive:true});"
        "tab.addEventListener('drop',function(e){"
        "e.preventDefault();tab.classList.remove('drag-over');"
        "var fromId=e.dataTransfer.getData('text/plain');"
        "reorderTabs(fromId,tab.getAttribute('data-tab-id'));});});"
        "}"
        "function reorderTabs(fromId,beforeId){"
        "if(fromId===beforeId)return;"
        "var sidebar=document.getElementById('sidebar');"
        "var fromTab=document.querySelector('[data-tab-id=\"'+fromId+'\"]');"
        "var beforeTab=document.querySelector('[data-tab-id=\"'+beforeId+'\"]');"
        "if(fromTab&&beforeTab){sidebar.insertBefore(fromTab,beforeTab);saveTabOrder();}"
        "}"
        "function saveTabOrder(){"
        "var order=[];"
        "document.querySelectorAll('.sidebar-tab').forEach(function(tab){"
        "order.push(tab.getAttribute('data-tab-id'));});"
        "localStorage.setItem('actionos_tab_order',JSON.stringify(order));"
        "var dd=document.getElementById('section-dropdown');"
        "order.forEach(function(tabId){"
        "var item=dd.querySelector('.section-dropdown-item[data-tab-id=\"'+tabId+'\"]');"
        "if(item)dd.appendChild(item);});"
        "}"
        "function restoreTabOrder(){"
        "try{"
        "var saved=localStorage.getItem('actionos_tab_order');"
        "if(!saved)return;"
        "var order=JSON.parse(saved);"
        "var sidebar=document.getElementById('sidebar');"
        "order.forEach(function(tabId){"
        "var tab=sidebar.querySelector('.sidebar-tab[data-tab-id=\"'+tabId+'\"]');"
        "if(tab)sidebar.appendChild(tab);});"
        "var dd=document.getElementById('section-dropdown');"
        "order.forEach(function(tabId){"
        "var item=dd.querySelector('.section-dropdown-item[data-tab-id=\"'+tabId+'\"]');"
        "if(item)dd.appendChild(item);});"
        "}catch(e){}}"
        "restoreTabOrder();"
        "initDragDrop();"
        # Tab rename on double-click
        "function initRename(){"
        "document.querySelectorAll('.tab-label').forEach(function(lbl){"
        "lbl.addEventListener('dblclick',function(e){"
        "e.stopPropagation();"
        "var tab=lbl.closest('.sidebar-tab');"
        "var tabId=tab.getAttribute('data-tab-id');"
        "var inp=document.createElement('input');"
        "inp.className='tab-label-input';"
        "inp.value=lbl.textContent;"
        "lbl.style.display='none';"
        "lbl.parentNode.insertBefore(inp,lbl);"
        "inp.focus();inp.select();"
        "function commit(){"
        "var val=inp.value.trim();"
        "if(val){lbl.textContent=val;saveTabNames();}"
        "lbl.style.display='';inp.remove();"
        "}"
        "inp.addEventListener('blur',commit);"
        "inp.addEventListener('keydown',function(ke){"
        "if(ke.key==='Enter'){ke.preventDefault();inp.blur();}"
        "if(ke.key==='Escape'){inp.value=lbl.textContent;inp.blur();}"
        "});"
        "});});}"
        "function saveTabNames(){"
        "var names={};"
        "document.querySelectorAll('.sidebar-tab').forEach(function(tab){"
        "var id=tab.getAttribute('data-tab-id');"
        "var lbl=tab.querySelector('.tab-label');"
        "if(lbl)names[id]=lbl.textContent;"
        "});"
        "localStorage.setItem('actionos_tab_names',JSON.stringify(names));"
        "}"
        "function restoreTabNames(){"
        "try{"
        "var saved=localStorage.getItem('actionos_tab_names');"
        "if(!saved)return;"
        "var names=JSON.parse(saved);"
        "Object.keys(names).forEach(function(id){"
        "var tab=document.querySelector('.sidebar-tab[data-tab-id=\"'+id+'\"]');"
        "if(tab){var lbl=tab.querySelector('.tab-label');"
        "if(lbl)lbl.textContent=names[id];}"
        "var ddItem=document.querySelector('.section-dropdown-item[data-tab-id=\"'+id+'\"] .section-dropdown-label');"
        "if(ddItem)ddItem.textContent=names[id];"
        "if(id===activeTab){"
        "var pl=document.getElementById('section-picker-label');"
        "if(pl)pl.textContent=names[id];}"
        "});"
        "}catch(e){}}"
        "restoreTabNames();"
        "initRename();"
        # Mobile edit mode: toggle, reorder, rename
        "function toggleEditMode(){"
        "var dd=document.getElementById('section-dropdown');"
        "var btn=document.getElementById('section-dd-edit-btn');"
        "var editing=dd.classList.toggle('editing');"
        "btn.textContent=editing?'Done':'Edit';"
        "}"
        "function moveSectionUp(tabId){"
        "var dd=document.getElementById('section-dropdown');"
        "var item=dd.querySelector('.section-dropdown-item[data-tab-id=\"'+tabId+'\"]');"
        "if(!item)return;"
        "var prev=item.previousElementSibling;"
        "while(prev&&!prev.classList.contains('section-dropdown-item'))prev=prev.previousElementSibling;"
        "if(!prev)return;"
        "dd.insertBefore(item,prev);"
        "var sidebar=document.getElementById('sidebar');"
        "var sTab=sidebar.querySelector('.sidebar-tab[data-tab-id=\"'+tabId+'\"]');"
        "var sPrev=sTab?sTab.previousElementSibling:null;"
        "if(sTab&&sPrev)sidebar.insertBefore(sTab,sPrev);"
        "saveTabOrder();"
        "}"
        "function moveSectionDown(tabId){"
        "var dd=document.getElementById('section-dropdown');"
        "var item=dd.querySelector('.section-dropdown-item[data-tab-id=\"'+tabId+'\"]');"
        "if(!item)return;"
        "var next=item.nextElementSibling;"
        "while(next&&!next.classList.contains('section-dropdown-item'))next=next.nextElementSibling;"
        "if(!next)return;"
        "dd.insertBefore(next,item);"
        "var sidebar=document.getElementById('sidebar');"
        "var sTab=sidebar.querySelector('.sidebar-tab[data-tab-id=\"'+tabId+'\"]');"
        "var sNext=sTab?sTab.nextElementSibling:null;"
        "if(sTab&&sNext)sidebar.insertBefore(sNext,sTab);"
        "saveTabOrder();"
        "}"
        "function initMobileRename(){"
        "document.querySelectorAll('.section-dropdown-label').forEach(function(lbl){"
        "lbl.addEventListener('click',function(e){"
        "var dd=document.getElementById('section-dropdown');"
        "if(!dd.classList.contains('editing'))return;"
        "e.stopPropagation();"
        "var item=lbl.closest('.section-dropdown-item');"
        "var tabId=item.getAttribute('data-tab-id');"
        "var inp=document.createElement('input');"
        "inp.className='section-dd-rename-input';"
        "inp.value=lbl.textContent;"
        "lbl.style.display='none';"
        "lbl.parentNode.insertBefore(inp,lbl);"
        "inp.focus();inp.select();"
        "function commit(){"
        "var val=inp.value.trim();"
        "if(val){"
        "lbl.textContent=val;"
        "var sTab=document.querySelector('.sidebar-tab[data-tab-id=\"'+tabId+'\"]');"
        "if(sTab){var sLbl=sTab.querySelector('.tab-label');if(sLbl)sLbl.textContent=val;}"
        "if(tabId===activeTab){"
        "var pl=document.getElementById('section-picker-label');"
        "if(pl)pl.textContent=val;}"
        "saveTabNames();"
        "}"
        "lbl.style.display='';inp.remove();"
        "}"
        "inp.addEventListener('blur',commit);"
        "inp.addEventListener('keydown',function(ke){"
        "if(ke.key==='Enter'){ke.preventDefault();inp.blur();}"
        "if(ke.key==='Escape'){inp.value=lbl.textContent;inp.blur();}"
        "});"
        "});});"
        "}"
        "initMobileRename();"
        # Fetch all badge counts in the background on page load
        f"function loadAllBadges(){{"
        f"fetch('{base}?action=count_all')"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "['home','unread','inbox','p1','bestcase','calendar','code','followup'].forEach(function(id){"
        "if(d[id]!==undefined){"
        "var b=document.getElementById('badge-'+id);"
        "if(b)b.textContent=d[id];"
        "var db=document.getElementById('dpbadge-'+id);"
        "if(db)db.textContent=d[id];"
        "if(id===activeTab){"
        "var pb=document.getElementById('section-picker-badge');"
        "if(pb)pb.textContent=d[id];"
        "}"
        "}"
        "});"
        # Gray badge: commit tasks needing review (not yet reviewed in home view)
        "if(d.commit_unreviewed!==undefined){"
        "var b=document.getElementById('badge-commit');"
        "if(b)b.textContent=d.commit_unreviewed;"
        "var db=document.getElementById('dpbadge-commit');"
        "if(db)db.textContent=d.commit_unreviewed;"
        "if('commit'===activeTab){"
        "var pb=document.getElementById('section-picker-badge');"
        "if(pb)pb.textContent=d.commit_unreviewed;}"
        "}"
        # Amber badge: total actionable commit tasks (today + overdue + undated)
        "if(d.commit!==undefined){"
        "var cb=document.getElementById('badge-commit-due-today');"
        "var cdb=document.getElementById('dpbadge-commit-due-today');"
        "if(d.commit>0){"
        "if(cb){cb.textContent=d.commit;cb.style.display='';}"
        "if(cdb){cdb.textContent=d.commit;cdb.style.display='';}"
        "}else{"
        "if(cb)cb.style.display='none';"
        "if(cdb)cdb.style.display='none';"
        "}"
        "}"
        "if(d.due_today!==undefined){"
        "var dtc=document.getElementById('due-today-count');"
        "var dtb=document.getElementById('due-today-badge');"
        "if(dtc)dtc.textContent=d.due_today;"
        "if(dtb){if(d.due_today>0){dtb.classList.remove('zero');}else{dtb.classList.add('zero');}}"
        "}"
        "}).catch(function(){});}"
        "loadAllBadges();"
        # Service worker registration + push notification setup
        f"var _vapidKey='{vapid_public_key}';"
        f"var _swUrl='{function_url.rstrip('/')}?action=sw';"
        f"var _subUrl='{function_url.rstrip('/')}?action=subscribe';"
        f"var _notifTestUrl='{function_url.rstrip('/')}?action=notify_test';"
        "function _urlB64ToUint8(b64){"
        "var p=b64.replace(/-/g,'+').replace(/_/g,'/');"
        "while(p.length%4)p+='=';"
        "var raw=atob(p);var arr=new Uint8Array(raw.length);"
        "for(var i=0;i<raw.length;i++)arr[i]=raw.charCodeAt(i);return arr;}"
        "function initServiceWorker(){"
        "if(!('serviceWorker' in navigator)||!('PushManager' in window))return;"
        "navigator.serviceWorker.register(_swUrl).then(function(reg){"
        "var btn=document.getElementById('notif-btn');"
        "var perm=Notification.permission;"
        "if(perm==='default'){"
        "if(btn)btn.style.display='flex';}"
        "else if(perm==='granted'){"
        "if(btn){btn.style.display='flex';btn.classList.add('active');}"
        "_ensureSubscribed(reg);}"
        "}).catch(function(err){console.warn('SW register failed:',err);});}"
        "function _ensureSubscribed(reg){"
        "reg.pushManager.getSubscription().then(function(sub){"
        "if(sub){_storeSub(sub);return;}"
        "if(!_vapidKey)return;"
        "reg.pushManager.subscribe({"
        "userVisibleOnly:true,"
        "applicationServerKey:_urlB64ToUint8(_vapidKey)"
        "}).then(function(newSub){_storeSub(newSub);})"
        ".catch(function(e){console.warn('Push subscribe failed:',e);});});"
        "}"
        "function _storeSub(sub){"
        "fetch(_subUrl,{"
        "method:'POST',"
        "headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify(sub.toJSON())"
        "}).then(function(){console.log('Push subscription stored.');});"
        "}"
        "function requestNotifPermission(){"
        "if(!('serviceWorker' in navigator)||!('PushManager' in window))return;"
        "Notification.requestPermission().then(function(perm){"
        "if(perm==='granted'){"
        "var btn=document.getElementById('notif-btn');"
        "if(btn)btn.classList.add('active');"
        "navigator.serviceWorker.ready.then(function(reg){_ensureSubscribed(reg);"
        "setTimeout(function(){fetch(_notifTestUrl);},500);});}"
        "else{alert('Notification permission denied. You can re-enable it in Settings > Safari > Notifications.');}"
        "});}"
        "initServiceWorker();"
        "</script>"
        "</body></html>"
    )
