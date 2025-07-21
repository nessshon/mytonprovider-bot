from typing import Any

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.text import Text

from ..utils.i18n import Localizer


class I18NJinja(Text):

    def __init__(self, key: str, when: WhenCondition = None):
        super().__init__(when=when)
        self.key_template = key

    async def _render_text(
        self,
        data: dict[str, Any],
        manager: DialogManager,
    ) -> str:
        try:
            localizer: Localizer = manager.middleware_data.get("localizer")
            rendered_key = self.key_template.format(**data)
        except KeyError as e:
            raise KeyError(
                f"Missing placeholder in localization key: {e} | data: {data}"
            )
        return await localizer(rendered_key, **data)
