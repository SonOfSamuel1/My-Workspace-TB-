"""ActionOS dashboard shell builder.

Renders the parent shell page: sidebar, header with quick-add bar,
and iframes for all ActionOS views. All iframes point back to the
same unified Lambda function URL.
"""

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
    base = function_url.rstrip("/") + f"?token={action_token}"

    # All tab URLs point to the same Lambda with view= param
    # Lazy-load strategy: only the first tab (Starred) preloads at page load.
    # All others load on first switchTab() call.
    tabs: List[Tuple[str, str, str, bool]] = [
        ("starred", "Starred", f"{base}&action=web&view=starred&embed=1", True),
        ("unread", "Unread", f"{base}&action=web&view=unread&embed=1", False),
        ("inbox", "Inbox", f"{base}&action=web&view=inbox&embed=1", False),
        ("commit", "@commit", f"{base}&action=web&view=commit&embed=1", False),
        ("p1", "P1", f"{base}&action=web&view=p1&embed=1", False),
        ("bestcase", "Best Case", f"{base}&action=web&view=bestcase&embed=1", False),
        ("calendar", "Calendar", f"{base}&action=web&view=calendar&embed=1", False),
        ("code", "Code", f"{base}&action=web&view=code&embed=1", False),
    ]

    # Generate sidebar tab HTML
    sidebar_tabs_html = ""
    for i, (tid, label, _url, _preload) in enumerate(tabs):
        active = " active" if i == 0 else ""
        badge_text = str(starred_count) if tid == "starred" else "..."
        sidebar_tabs_html += (
            f'<div class="sidebar-tab{active}" id="tab-{tid}" '
            f'draggable="true" data-tab-id="{tid}" onclick="switchTab(\'{tid}\')">'
            f'<span class="tab-label">{label}</span>'
            f'<span class="badge" id="badge-{tid}">{badge_text}</span>'
            f"</div>"
        )

    # Generate iframe HTML (lazy: non-first tabs use about:blank)
    iframes_html = ""
    for i, (tid, _label, url, preload) in enumerate(tabs):
        display = "" if i == 0 else "display:none;"
        src = url if preload else "about:blank"
        iframes_html += (
            f'<iframe id="frame-{tid}" src="{src}" style="{display}"'
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
    first_badge = str(starred_count)
    dropdown_items_html = ""
    for i, (tid, label, _url, _preload) in enumerate(tabs):
        active_cls = " active" if i == 0 else ""
        check = "&#10003;" if i == 0 else "&nbsp;&nbsp;&nbsp;"
        badge_init = str(starred_count) if tid == "starred" else "..."
        dropdown_items_html += (
            f'<div class="section-dropdown-item{active_cls}" data-tab-id="{tid}" '
            f"onclick=\"selectSection('{tid}')\">"
            f'<span class="section-dropdown-check">{check}</span>'
            f'<span class="section-dropdown-label">{label}</span>'
            f'<span class="badge section-dropdown-badge" id="dpbadge-{tid}">{badge_init}</span>'
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
        '<link rel="icon" type="image/png" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAACJklEQVR4nNWWTa6iQBSFb/1gAJ0S2IIx6BqcaPxJZB9ux1XowDiXhC1o3IOKAzVRJELV7UHZtO3rVvOEwTszKrnfoVK36h6CiAAAAIiIiJRS9ZkkyeVyEUIQQuD/QkTOua7rmqapFSEEpTSrIspASqnQ8/l8NpstFovtdns+n4UQT+hKnPNKpWLbdqPR8Dyv2WzeAwERhRCIuN1ue73eS9xLDQaDMAwzLAghhBBhGLquCwCMMc45Y0xt801RSrNCAKjX67vdTpEhTVNEbLfbAFAqlT7fgYL0ej1ETNMUENH3fQDgnH9OV1KoIAgQkQLAZDJ53irfECFkPB4DAAWA5XKpejQvuqItl0sAoNfrNQxDtZqjAQCEYZgkCY3jOIqiIgyiKIrjmEoppZR5oe+VpqkQghaBvlfhBi96/53Lkabp9w2eF7+jfxsQQhDRMIzRaGTbtpTy601Ub/vhcBgOh8fjUZV8RRV+BrDf7x3HUX+dF1OhHMfZ7/c//5B//kW7jboi0GruUl3Xy+UyFNBFpmkahkE1TbMsqwgDy7I0TaMAUK/XVTjI0YAQomIKIGIQBFDA0Pd9HxFvsaXb7UKusaXVat1iSxa8arUa/B283s9eD8GrWq1uNptb8LqPjv1+//MddDqd9XqdYR/Dr+/70+l0tVodDofL5XI6nV5ObMaYaZq2bbuu63leq9W6B/55xB/iO/xO8M8NEJExput6dn5qeGQ9+QsbIl6xb3cpAQAAAABJRU5ErkJggg==">'
        '<link rel="apple-touch-icon" href="data:image/png;base64,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">'
        '<link rel="manifest" href="data:application/manifest+json,%7B%22name%22%3A%22ActionOS%22%2C%22short_name%22%3A%22ActionOS%22%2C%22description%22%3A%22Personal%20action%20dashboard%22%2C%22icons%22%3A%5B%7B%22src%22%3A%22data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAAMAAAADACAIAAADdvvtQAAATI0lEQVR4nO2dW2wU1RvAz5yZnd1y%2BZdLSkuhtF2qlkIj0QCKmChRAtGQ4JsmBB%2F00Qfjg0%2B%2B6ZMmXkIMEXzRBIMQHwz4AN4CRoIIwlYutdTGiilQaNp0L3M7c%2F4PX%2Fd09szs9jLbvX6%2FB7KdLtszc377fd85M3NG4ZyT8iH%2BOudcURTXdQkhlFLGGCGKpqmu6zLGFEVRVVVRlDI2tZRwzk3TdBwnGo1GIhHDMFzXbYjFTNsinEQiEcaYqqqEEEppeQ%2BLUmKBOOf5%2FqI4EPUjyuyBLxhzmUIUQgh80%2BBfOJ6KooBMJVaqFALxLCQrh6IoaEkRgcPruq7ruuI4q6oKUWpBWUCBhDfFkqa82bZkhP9qgUmMMc45pXRBTVoQgcT3YPbhFN4vApVolVc7SmnRm1qBwNGDvYYkRTyRm8zlq8g5Z4wxx3E51zQtEokUvbVFFkjs%2FIw7KaIuIYRSOhs5LMuCr5Q4rLWHoii6rs%2FmnRBgFA8F3sw5tyzLdV1VVSORSBHrh6IJJNQpoIKQBjK09N%2Fv379%2F586d%2B%2Ffv3717d2Ji4tatW7quj4yM3L17NxaLGYYxODjoOI6u65ZlFaXNFQV0KqV0%2Ffr1ixcvtm07Go1u2LCBMdbY2BiPx1VV7ezsXLRoUWtr6%2BLFi6X%2FLhJWAZk4547jOI6jquosNZ252eEFEk4UUAf08kqTSqWGhoYuXbrU399%2F5cqVf%2F%2F9986dO2NjYzUcXcKjKEo0Gl21atWaNWs6Ojp6enq6uroeffTRzs7OWCwm3uY4ToGgLqKRruvha6OwAjHGSP5aB9wSvzUMI5FIXLhw4ddff%2F3tt9%2F%2B%2Becf%2BO85DcqKKD7QO1cUpqnVgvdIwmtRFwZ%2BuzRNi8fjW7du3bFjxzPPPPPII4%2FAdv%2BX1ovruoZhqiqNRqOhmsvni%2Bu6tm1D5Az8reM44sfLly%2B%2F%2FfbbYt8EqqpqmqaqauHYiwBwiCC6wKGTwkwkEtm2bdt777138%2BZNcfAdxwGZ%2FJimmUql8nXibJinQIyxAs0S6qRSqePHj%2B%2Fevdu7n15jSt4FNQgoJY3VY7HYvn37Tp06JfrI%2B32WOiuVStmWNT8T5iMQ2JPvV9DiZDL5ySefPPTQQ2KXUJoSIGQSW55%2B%2Buljx47BADbfd9513XQ6bRjGPGSYs0CO4%2BSLeMKqr7%2F%2BuqenB3ZA2h%2BkNMA4VwT%2Bbdu2nTlzRuomiUwmk8lk5urD3ATKZ4%2BYRO%2Fr69uzZw802rsDSLnwDsf2798%2FPDzM84ciwzDn6tAcBMpnj9j40UcfLV26lMx6YhApGaJ4aG1tPXbsmNRxXkxzbg7NVqB89kA8HB0d3bt3L7QVE1bFomkavHjrrbfAksB0NieHZiVQPnts2%2BacDw4Owvi8ri7ZqVJEcti5c%2Bfdu3fzOWQYxiwdmlmgfGMu2Hj16tX169cTj91I5QOd1dPTA9NFgf2byWRM0wwrkDQfKIDYc%2FXq1dWrVxO0pwqBLlu3bt2NGzfyOZROp6Gj5ylQYXsSiQTYg0VPlQIdt65t3fXr10W3SgLMOE9dSKDAwR4o1dfX19raStCeKge6r62t7dq1azwoDjHGUqnUfARijPnVgz%2BQSCTQnpphKg6tW9ff38%2BDxvamaRaYpA4WKDB5wUePjo7G43GCdU8NAQ5t3LhxbGwMel%2Fq%2BnQ6nW%2F%2BOlggf%2FKCa2yTyeQTTzxBMPbUHBAOdu7caRiGOKHpjR3pdHq2AhVIXi%2B%2F%2FDLB2FOjQLe%2B8cYbPKgYMk3TCjpjHyCQ%2Fz%2FDlo8%2F%2FpgQshAXZiMVAjh0%2FPhxvwYu5%2Bl02p%2FdZIH84Qc%2B6Pfff4crIHGuuYaBC9aam5uHh4fFjUECy7L8QUgWSPbOdUEpLH3qBOjiV155JVAG%2F%2FmNHIHyhZ%2FPPvuMYOlTH4hlCL7%2F%2Fnu%2FQ6ZpSvONRNLFm%2BTgKp9kMhmPxwvfdIHUEtDRmzdvhkUdJCWkIES8v5N0A9cOHTpEMHnVGdDdX331Ffed4oBxfoBA0uhfhJ%2Fu7m4MP%2FUGZLHNmzebpikFIdu2vWfppwWSwg%2F8ePToUVI3N6UjXqDTT5486XfDm8WmbzeWymfwbseOHf7bkJF6ADr9xRdf5L4TZN4sRkT%2B8r5JzP1AKMO5n%2FpEUZSGhgb%2FSVbbtsWE0FRu4pz789SXX34JS6nx%2BrinGJGglGYymRMnThDPQjOEEFVVp3%2F0F0BQMRmG0dXVRbAAqmMgi23ZsgUGWN5SGkb4UylMKoBApjNnzhBcrrC%2Bgd6PRCJ9fX1SFoM1QKdSGM%2BuhwVAwrp06RLB6Z%2F6hnOuqqpt26dPnya5WYxSCp4EpCfIWRcuXCB1s6IKUphz586R3GJGrMlMpNAEiS2VSrW1tRFMYXUPSNPe3p5MJnnuxYqmaUzVQF6B4PWlS5ewdkZINoJompZIJCRV4EJpKiUpiEuJRAIWZCxPq5GKAcogx3GuXbtGcssgRVGm54G8WwkhiUSCYP5CCCFZDa5fv%2B7f7rpusED9%2Ff0EK2iEEJLV4MaNGyRoUjAnhcF8tGEYt27dIigQ4mFoaAieeiO2wILdAUtbTk5Ojo2NERQIIYRk656RkZFUKgV1D2yfWu7TWxbB7%2B7cufPgwQOCAiEexsfHR0dHSa4VjuPkpDT43e3btwPPrSL1TCaTmZiYkDaCJ%2FLKqePj4wSHYEgWGMlzzgcHB4knAlFKdV2n3rXiRQorS0ORCkdaJ59znskYAQs3%2F%2FfffwQjEOIBZPjrr79I7pO4aOAizjgBjQRiGIa0paEhRqVz9ISQgYEBgkMwxIdfCcuycmogwDTNUjUJqQ5AHTgd5h2eW5ZF%2FZeS%2BR9mhiAkKAJpmpZTA8G84sjISGkbhlQH%2FnFVNBqdjkBwYatt27dv3yZYAyE%2BoIiWnocXMN2Mq3AgEhBNhoaGLMvyng4j%2FmuiVVUN%2BwxEpJ6QBYLlFMvSFKTCgetZpY0BKQznoJHZg6fckVCgQEgoUCAkFCgQEgoUCAkFCoSEAgVCQoECIaFAgZBQoEBIKFAgJBQoEBIKFAgJBQqEhAIFQkKBAiGhQIGQUKBASChQICQUKBASChQICQUKhIQCBUJCgQIhoUCBkFCgQEgoUCAkFCgQEopqFUhVVf8S6VUKrJVbpftSlWtJKYriXxu0ehEL5UprN1UF1ScQLOS4e%2FfuAwcOdHR01MAzPSYmJk6fPn3w4EHDMKrPIelxu4ZhxONxEvRosUoAlgR9%2FfXXec3x3XffRaNR%2F9O3KgGQIR6Pw3NSvY%2FeraYIBJmrpaXl%2FfffJ4TYtg0PASl3u4oAY2zPnj379%2B8%2FcuSIqqpVlKCrSSBKKWPssccea2xsdF03EomUu0XFxHXdnTt3HjlypNwNmRuVmKcKUxshp2aopggEo5U%2F%2FvhjYmKisbGxxlKYrus%2F%2FvhjuRsyd0Q1hEV0ecEiuhQwxiilhw8fHh4efvXVV2tsGG%2BaJg7jS0EFfkeLQsXuV%2B1EIIBnn%2BIJlLs5YYFzMtAr5W7LnKlKgQghVTRTMiPSs0iri8rNU0hVgAIhoUCBkFCgQEgoUCAkFCgQEgoUCAkFCoSEAgVCQoECIaFAgZBQoEBIKFAgJBQoEBIKFAgJBQqEhAIFQkKBAiGhQIGQUKBASChQICQUKBASChQICQUKhIQCBUJCgQIhoUCBkFCgQEgoAgSqxjUikHIhC6Sq6qJFi8rSFKTCCVxOXxbIdV3HcUrVJKSasG3bn52mBYLF1XRdb29vJxW8WhZSLlauXKlpmuQQ9f4MrxsaGkrdNKSygWiyevVqWBhOBBfOOTVNs6xtQ6oG%2F8rutm1Tf8WDozAkEH%2BscV2X6rru%2FZkQ0tPTQ7AGQjyADG1tbSQ3vmialiMQEIvFStk4pFpoaWkhfoEMw5De51cKQUhQCrMsi3qXJ4ZI1dXVRbASQjyADP75Hc45jcViUrkDxTYKhEg0NjZKW3Rdp5ZleZ%2FZSQhZu3YtIcR1XayjEQAMWb16tbTRcZyABx8vW7YM62hEIJ7%2FsmLFCuJJYfCCaprmfSshpLm5eeXKlWVoKVLBLF%2B%2BvKmpieTWQKqqykU053zRokUQrCr5gT1IyQBjVq1aJYUVeMQThadoe7eqqtrR0VHiViIVixib67rurYw554o%2FxoBMGzZsIDgZjRBCshp0d3eToAcLUUqpf8QOZzNwJI%2BQrAYQU6TtiqLAKGxaFIhJGzdu1DSNMYZBCClwhlRRFMI5N01TPMQQXiSTSZh2xDq6zgEB1qxZMz4%2BLj3sEi5QBD8U70DMdd3Fixdv2bKFoEB1D4Scxx9%2FvLGx0VtBi2KIEkIoVbzFEbx%2B7rnnCJZBdQ8Y09vbS3IraHFdIiXZqCN%2BB1HnqaeeikQiWAbVOfBs2ueff574TqNO%2FQiJDR7nLMog13UZY5DFVFUtT9uRcgOh5OGHH%2FY%2F7RsKoKkaCFTylkGMMUrp3r17y9h6pOyAQC%2B88EI0GnUcxzuFOP0m8MiyLOEU55wxxjm%2FefNmQ0ODoiiYxeoTRVEopefPn%2BecO44j9HAcR%2FxIhDHeLCYc2rVrF8EsVpdQShVF2b59O5Q0Xjds2wY9pgXinGcyGe%2BbQLFvv%2F2W4GC%2BLoGo8cUXX3grHqkAyhHINE3pfa7rmqbZ29urKAoGoboCws%2FatWvHx8elCMQYCxbIn8UgCB09epRgEKozIF4cPHhQqn6k%2FJUjEGQxr2ugnmEYmzZtIuhQ3QDhp6OjY2JiQgo%2FrutaluV1Jkcg27ZN0%2FQHoZMnTxIspesGuEj1888%2FDww%2F0pYcgfxBSHzESy%2B9RNChOgC6eMeOHYwxb6oCpPATIJBlWdKbGGOu6w4NDa1YsQLnhGobmPiJRqNXrlzxhx%2Fv9E9egVzXTafTPCcG5VTTmqahQ7UKJK8PPvjAbw8EFyk7BQgE7zMNU9oIH%2Ffaa6%2BJP4PUGNCt%2B%2FbtC7QnMPwEC8Q5T6fTUv6Du8iSyeT27dsJFkM1B3Rob2%2Fv2NgYFC1S7%2Furn0ICOY6TTqeljaDU8PBwZ2cnQYdqCJigaW1tvXnzpuhoL5Zl%2BTcWEohzbhiGNKTn2ch2%2BfLlpUuXEpwZqgmgE2Ox2M8%2F%2F8x9Zy2g0%2F0bZxaIc55OyYlMOPTTTz%2F973%2F%2FI%2BhQlSPsOXXqFA8qfVzXtczg5DWzQIyxVCrlL7zhz%2Fzwww%2BwXAPmsioF7GloaAB7AsOM5bnhYs4CwYf6iyHxx86dOwe5DMdlVQd87WewJ3%2FpM1uBOOemaUpXegAQhy5evBiPxwk6VFVAZ61Zs%2BaXX37hQZmLB521mKdAnPNMJiOdqBd%2Fg3M%2BMDCwdetWkmcpfKSiUBQF7NmwYcOff%2F7J88Qe27YLFM5zFggc8g%2FKeFbeycnJAwcOQBOxJKpYRNfs2bPn%2Fv37PF%2FscWZrzxwEKuCQSJOHDx9evnw5gRvucXRWSVA6tRBULBZ79913wZt8mWv29sxNIJ4%2Fl8FtQJzz%2Fv7%2Bffv2QaNVVUWNyo73atLt27dfvHhRdFl4e%2BYsEDgUWFNzj9HffPMN3MtICKGUYm1UFuDIw%2Bvu7u5PP%2F0UTkfYtp3PnnznKwowZ4E454ZhpNPpwEaIi0gymcyRI0e8a4JAQEKTFhqRrYD29vZDhw4lk0nRQYF9Kt3XNXvmIxDn3LasVCqVb5gntqfT6RMnTuzatcu7S5qmYUwqLpCnpCtttmzZ8uGHH46Ojk51WZ7AA7dOzDjfk495CsSz89SBZTXPnr0XPyYSiXfeeWfTpk3ePRS7LYITXNAUGKhQOEAcJXHopCPT3d395ptvwgQP4DhOvtlkx3HMmeaaCzO9sMv8MAzDdd1YLBZYL4NJQgjHca5cuXL27Nnz58%2BfPXv23r17hY%2BU%2BEz4HO8WUtMrh0hfM5LdWTgO%2FvcvWbKkt7f32Wef3bVr15NPPikeVuE4Tr5gD%2FaIaaH5NzV8NzDGLMuilOq6ni9OgOPeKaJ79%2B7dunVrYGDg2rVr%2Ff39g4ODDx48IIS0tLRQSvv7%2B1OplPcTNE3DZ3ESQhRFWbZsWXNzc1tbW09PT29vb1dXV3t7u3ddVDAj34Qcz16mrGla%2BGFyEQQC4LyJpmkFrnkV2c0%2FUcQYm5ycZIwtWbKEUvr3338PDQ3du3dvfHw8Fos1NTW1tLSMjIz09fUNDAyMjo5OTk6m02nTNFVVhesNirIX5UVVVcaYrusdHR2wxOCyZcs6Oztt225qalq7du3KlSubm5ubmpqampqkx7%2BJ4FR4pAKjHFVVizXfWzSBCCE8e9dZ4Wgk3iyWqJ7fxCNMPsEyxbWxjhEs1KSqqv%2FZgH7EARRVUeE3Q5nsHdsXhWIKJLBt23EYVYg66wGX1AyIVcSzkJG3FKj56QBR6IjjQLJHQNwYM8sjIO4MLLo6U61auFIUoiUUvzDOKuLEdA1X0CT0kFOUCvD1W9AzSwsokEDMLpLs2EoM2hf6T9cJcGylp1aUJk6XQiCB%2BFqIXfWGZfiWwGCNe54tjQjEOqmQ46S%2Bm00xVHRKehWYf2wpxg5QBcNgSlEUwzDgFkk4QaOqqv%2FBeDUMz04cw6gWXuu6DkcJHi4gonh5D8v%2FAVp7N6ooWuw4AAAAAElFTkSuQmCC%22%2C%22sizes%22%3A%22192x192%22%2C%22type%22%3A%22image%2Fpng%22%2C%22purpose%22%3A%22any%20maskable%22%7D%5D%2C%22theme_color%22%3A%22%233d1b42%22%2C%22background_color%22%3A%22%231a1a1a%22%2C%22display%22%3A%22standalone%22%2C%22orientation%22%3A%22portrait%22%2C%22start_url%22%3A%22.%22%7D">'
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
        ".refresh-btn{background:var(--border);border:1px solid var(--border);color:var(--text-1);"
        "font-size:13px;font-weight:600;padding:6px 14px;border-radius:6px;cursor:pointer;flex-shrink:0;}"
        ".refresh-btn:hover{background:var(--border-h);}"
        ".notif-btn{background:transparent;border:none;color:var(--text-2);cursor:pointer;"
        "width:32px;height:32px;border-radius:6px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}"
        ".notif-btn:hover{background:var(--border);color:var(--text-1);}"
        ".notif-btn.active{color:var(--accent-l);}"
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
        "height:calc(100vh - 48px - 44px);}"  # header + quick-add bar
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
        ".sidebar-tab.dragging{opacity:0.4;}"
        ".sidebar-tab.drag-over{border-top:2px solid var(--accent);}"
        ".tab-label-input{font:inherit;font-size:14px;font-weight:600;width:80px;"
        "border:1px solid var(--accent);border-radius:3px;padding:1px 4px;outline:none;"
        "background:var(--bg-s2);color:var(--text-1);}"
        ".main-content{flex:1;position:relative;overflow:hidden;background:var(--bg-base);}"
        ".main-content iframe{display:block;position:absolute;top:0;left:0;width:100%;height:100%;"
        "border:none;background:var(--bg-base);}"
        # Mobile section picker
        ".section-picker{display:none;align-items:center;gap:8px;background:var(--bg-s2);"
        "border:1px solid var(--border-h);border-radius:8px;padding:7px 12px 7px 14px;"
        "cursor:pointer;touch-action:manipulation;}"
        ".section-picker-label{font-size:14px;font-weight:600;color:var(--text-1);}"
        ".section-picker-chevron{font-size:11px;color:var(--text-2);margin-left:2px;}"
        ".section-dropdown{display:none;position:fixed;top:49px;left:0;right:0;z-index:9999;"
        "background:var(--bg-s1);border-bottom:1px solid var(--border-h);"
        "box-shadow:0 4px 12px rgba(0,0,0,.3);"
        "overflow-y:auto;max-height:calc(100dvh - 56px);will-change:transform,opacity;}"
        ".section-dropdown.open{display:block;animation:ddSlide .15s ease;}"
        "@keyframes ddSlide{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}"
        ".section-dropdown-item{display:flex;align-items:center;gap:12px;padding:15px 20px;"
        "font-size:15px;font-weight:500;color:var(--text-2);cursor:pointer;"
        "border-bottom:1px solid var(--border);touch-action:manipulation;}"
        ".section-dropdown-item:last-child{border-bottom:none;}"
        ".section-dropdown-item.active{color:var(--text-1);background:var(--accent-hbg);}"
        ".section-dropdown-check{width:20px;font-size:14px;color:var(--accent-l);flex-shrink:0;}"
        ".section-dropdown-label{flex:1;}"
        ".section-dropdown-badge{margin-left:auto;}"
        ".section-dd-header{display:flex;align-items:center;justify-content:space-between;padding:12px 20px;border-bottom:1px solid var(--border);}"
        ".section-dd-title{font-size:13px;font-weight:600;color:var(--text-2);text-transform:uppercase;letter-spacing:.5px;}"
        ".section-dd-edit-btn{background:none;border:none;color:var(--accent-l);font-size:14px;font-weight:600;cursor:pointer;}"
        ".section-dd-arrows{display:none;margin-left:auto;gap:4px;}"
        ".section-dropdown.editing .section-dd-arrows{display:flex;}"
        ".section-dropdown.editing .section-dropdown-check{display:none;}"
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
        ".qa-fab{display:none;position:fixed;bottom:24px;right:20px;width:56px;height:56px;"
        "border-radius:50%;background:var(--fab-bg);color:#fff;"
        "border:none;cursor:pointer;align-items:center;justify-content:center;"
        "box-shadow:0 2px 8px rgba(0,0,0,.25);z-index:1000;touch-action:manipulation;}"
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
        ".section-picker{display:flex;}"
        ".sidebar{display:none!important;}"
        ".app-body{flex-direction:column;height:calc(100vh - 48px);}"
        ".main-content{flex:1;height:100%;}"
        ".quick-add-bar{display:none;}"
        ".qa-fab{display:flex;}"
        "}"
        "::-webkit-scrollbar{width:6px;}"
        "::-webkit-scrollbar-track{background:transparent;}"
        "::-webkit-scrollbar-thumb{background:var(--scrollbar);border-radius:3px;}"
        "</style>"
        "</head><body>"
        # Header
        '<div class="header">'
        f'<a class="header-title-link" href="{function_url.rstrip("/")}?action=web&token={action_token}" '
        f'onclick="goHome(event)">ActionOS</a>'
        # Mobile section picker (hidden on desktop)
        + f'<button class="section-picker" id="section-picker" onclick="toggleSectionPicker()">'
        f'<span class="section-picker-label" id="section-picker-label">{first_label}</span>'
        f'<span class="badge" id="section-picker-badge">{first_badge}</span>'
        f'<span class="section-picker-chevron">&#9660;</span>'
        f"</button>"
        + '<button class="refresh-btn" onclick="refreshActive()">&#8635; Refresh</button>'
        + '<button class="notif-btn" id="notif-btn" onclick="requestNotifPermission()" title="Enable notifications" style="display:none">'
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>'
        '<path d="M13.73 21a2 2 0 0 1-3.46 0"/>'
        "</svg></button>"
        "</div>"
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
        '<button class="qa-fab" id="qa-fab" onclick="openMobileSheet()">'
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
        # JavaScript
        "<script>"
        "var _resizeTimer;function autoResize(el){clearTimeout(_resizeTimer);_resizeTimer=setTimeout(function(){el.style.height='auto';el.style.height=el.scrollHeight+'px';},50);};"
        "var activeTab='" + tabs[0][0] + "';"
        "var tabIds=" + tab_ids_json + ";"
        "var tabUrls=" + tab_urls_json + ";"
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
        "if(tab===activeTab)return;"
        "activeTab=tab;"
        "tabIds.forEach(function(id){"
        "document.getElementById('tab-'+id).className='sidebar-tab'+(id===tab?' active':'');"
        "document.getElementById('frame-'+id).style.display=id===tab?'block':'none';"
        "});"
        "var frame=document.getElementById('frame-'+tab);"
        "if(frame&&frame.src.indexOf('about:blank')!==-1){"
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
        "item.querySelector('.section-dropdown-check').innerHTML=isActive?'&#10003;':'&nbsp;&nbsp;&nbsp;';"
        "});"
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
        f'fetch("{function_url.rstrip("/")}?action=create_task&token={action_token}",'
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
        f'fetch("{function_url.rstrip("/")}?action=create_task&token={action_token}",'
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
        "}"
        "if(e.data&&(e.data.type==='markread'||e.data.type==='unstar'||e.data.type==='skip-inbox')){"
        # Reload starred frame when an email is actioned from the viewer
        "var sf=document.getElementById('frame-starred');"
        "if(sf&&sf.src.indexOf('about:blank')===-1)sf.contentWindow.location.reload();"
        "}"
        "if(e.data&&e.data.type==='viewer-open'){closeSectionPicker();}"
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
        f"fetch('{base}&action=count_all')"
        ".then(function(r){return r.json();})"
        ".then(function(d){"
        "['unread','inbox','commit','p1','bestcase','calendar','code'].forEach(function(id){"
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
        "}).catch(function(){});}"
        "loadAllBadges();"
        # Service worker registration + push notification setup
        f"var _vapidKey='{vapid_public_key}';"
        f"var _swUrl='{function_url.rstrip('/')}?action=sw';"
        f"var _subUrl='{function_url.rstrip('/')}?action=subscribe&token={action_token}';"
        f"var _notifTestUrl='{function_url.rstrip('/')}?action=notify_test&token={action_token}';"
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
