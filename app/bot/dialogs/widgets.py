from aiogram.types import InlineKeyboardButton
from aiogram_dialog.api.internal import RawKeyboard
from aiogram_dialog.api.protocols import DialogManager
from aiogram_dialog.widgets.kbd import ScrollingGroup


class PaginatedScrollingGroup(ScrollingGroup):

    async def _render_pager(
        self,
        pages: int,
        manager: DialogManager,
    ) -> RawKeyboard:
        if self.hide_pager:
            return []
        if pages == 0 or (pages == 1 and self.hide_on_single_page):
            return []

        last_page = pages - 1
        current_page = min(last_page, await self.get_page(manager))

        buttons = []
        if pages <= 5:
            for i in range(pages):
                text = f"· {i + 1} ·" if i == current_page else str(i + 1)
                buttons.append(InlineKeyboardButton(
                    text=text,
                    callback_data=self._item_callback_data(i),
                ))
        elif current_page <= 2:
            for i in range(min(3, pages)):
                text = f"· {i + 1} ·" if i == current_page else str(i + 1)
                buttons.append(InlineKeyboardButton(
                    text=text,
                    callback_data=self._item_callback_data(i),
                ))
            buttons.append(InlineKeyboardButton(
                text=f"{current_page + 2} ›",
                callback_data=self._item_callback_data(current_page + 1),
            ))
            buttons.append(InlineKeyboardButton(
                text=f"{last_page + 1} »",
                callback_data=self._item_callback_data(last_page),
            ))
        elif current_page >= last_page - 2:
            buttons.append(InlineKeyboardButton(
                text="« 1",
                callback_data=self._item_callback_data(0),
            ))
            buttons.append(InlineKeyboardButton(
                text=f"‹ {current_page}",
                callback_data=self._item_callback_data(current_page - 1),
            ))
            for i in range(max(0, last_page - 2), pages):
                text = f"· {i + 1} ·" if i == current_page else str(i + 1)
                buttons.append(InlineKeyboardButton(
                    text=text,
                    callback_data=self._item_callback_data(i),
                ))
        else:
            buttons.append(InlineKeyboardButton(
                text="« 1",
                callback_data=self._item_callback_data(0),
            ))
            buttons.append(InlineKeyboardButton(
                text=f"‹ {current_page}",
                callback_data=self._item_callback_data(current_page - 1),
            ))
            buttons.append(InlineKeyboardButton(
                text=f"· {current_page + 1} ·",
                callback_data=self._item_callback_data(current_page),
            ))
            buttons.append(InlineKeyboardButton(
                text=f"{current_page + 2} ›",
                callback_data=self._item_callback_data(current_page + 1),
            ))
            buttons.append(InlineKeyboardButton(
                text=f"{last_page + 1} »",
                callback_data=self._item_callback_data(last_page),
            ))

        return [buttons]
