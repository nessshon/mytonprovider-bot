from aiogram import F
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    CallbackQuery,
    ChatMemberUpdated,
)

from ..utils import delete_message
from ..utils.i18n import Localizer
from ...database.models import ProviderModel, UserModel
from ...database.unitofwork import UnitOfWork


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
        subscriptions = user.subscriptions if user and user.subscriptions else None
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
    await delete_message(call.message)
