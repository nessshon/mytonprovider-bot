BAGS_PER_PAGE = 10


def build_pagination_buttons(
    current_page: int,
    total_pages: int,
) -> list[dict[str, str]]:
    if total_pages <= 1:
        return []

    page = current_page + 1
    buttons = {}

    if total_pages <= 5:
        for p in range(1, total_pages + 1):
            buttons[p] = str(p)
    elif page <= 3:
        for p in range(1, 4):
            buttons[p] = str(p)
        buttons[4] = "4 ›"
        buttons[total_pages] = f"{total_pages} »"
    elif page > total_pages - 3:
        buttons[1] = "« 1"
        buttons[total_pages - 3] = f"‹ {total_pages - 3}"
        for p in range(total_pages - 2, total_pages + 1):
            buttons[p] = str(p)
    else:
        buttons[1] = "« 1"
        buttons[page - 1] = f"‹ {page - 1}"
        buttons[page + 1] = f"{page + 1} ›"
        buttons[total_pages] = f"{total_pages} »"
        buttons[page] = str(page)

    buttons[page] = f"· {page} ·"

    return [
        {"id": str(p - 1), "label": label}
        for p, label in sorted(buttons.items())
    ]
