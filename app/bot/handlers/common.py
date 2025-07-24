from contextlib import suppress

from aiogram.enums import ContentType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    Message,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    CallbackQuery,
    ChatMemberUpdated,
)
from aiogram_dialog import DialogManager, ShowMode

from ..dialogs import states
from ...database import UnitOfWork
from ...database.models import ProviderModel, UserModel
from ...utils.i18n import Localizer


async def my_chat_memeber(
        update: ChatMemberUpdated,
        uow: UnitOfWork,
        user_model: UserModel,
) -> None:
    user_model.state = update.new_chat_member.status
    await uow.user.upsert(user_model)


async def providers_inline(
        query: InlineQuery,
        uow: UnitOfWork,
        localizer: Localizer,
) -> None:
    offset, limit = int(query.offset or 0), 20
    query_type = (query.query or "").strip().lower()

    user_id, filters = query.from_user.id, {}
    list_type = "my_providers" if query_type.startswith("my") else "list_providers"

    if list_type == "my_providers":
        user = await uow.user.get(user_id=user_id)
        subscriptions = (
            await uow.user_subscription.list(user_id=user.id) if user else []
        )
        filters["pubkey"] = [s.provider_pubkey for s in subscriptions]

    total = await uow.provider.count(**filters)
    providers = await uow.provider.list(
        offset=offset,
        limit=limit,
        order_by=[ProviderModel.rating.desc()],
        **filters,
    )

    results = [
        InlineQueryResultArticle(
            id=provider.pubkey,
            title=await localizer(
                f"inlines.{list_type}.title",
                provider=provider,
            ),
            description=await localizer(
                f"inlines.{list_type}.description",
                provider=provider,
            ),
            thumbnail_url=await localizer(
                f"inlines.{list_type}.thumbnail_url",
                provider=provider,
            ),
            input_message_content=InputTextMessageContent(message_text=provider.pubkey),
        )
        for provider in providers
    ]

    next_offset = str(offset + limit) if offset + limit < total else ""
    await query.answer(results, cache_time=5, is_personal=True, next_offset=next_offset)


async def hide_callback_query(call: CallbackQuery) -> None:
    with suppress(TelegramBadRequest):
        await call.message.delete()


async def default_message(
        message: Message,
        dialog_manager: DialogManager,
        uow: UnitOfWork,
) -> None:
    pubkey = message.text.strip() if message.content_type == ContentType.TEXT else None

    def is_valid_pubkey(_pubkey: str) -> bool:
        if len(_pubkey) != 64:
            return False
        try:
            bytes.fromhex(_pubkey)
            return True
        except ValueError:
            return False

    if not pubkey or not is_valid_pubkey(pubkey):
        await dialog_manager.start(
            state=states.MainMenu.INVALID_INPUT,
            show_mode=ShowMode.EDIT,
        )
    else:
        state, data = (
            (states.ProviderMenu.MAIN, {"provider_pubkey": pubkey})
            if await uow.provider.exists(pubkey=pubkey)
            else (states.MainMenu.NOT_FOUND, None)
        )
        await dialog_manager.start(
            state=state,
            data=data,
            show_mode=ShowMode.EDIT,
        )

    with suppress(TelegramBadRequest):
        await message.delete()
