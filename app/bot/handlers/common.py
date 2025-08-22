from aiogram.enums import ContentType
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
from ..utils import delete_message, generate_password_hash, is_valid_pubkey
from ...config import ADMIN_IDS, ADMIN_PASSWORD
from ...database import UnitOfWork
from ...database.models import ProviderModel, UserModel, UserSubscriptionModel
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


async def enter_password_message(
    message: Message,
    dialog_manager: DialogManager,
    uow: UnitOfWork,
) -> None:
    if message.content_type != ContentType.TEXT:
        await delete_message(message)
        return

    user: UserModel = dialog_manager.middleware_data["user_model"]
    pubkey = dialog_manager.dialog_data.get("provider_pubkey")
    telemetry = await uow.telemetry.get(provider_pubkey=pubkey)
    telemetry_pass = telemetry.telemetry_pass if telemetry else None

    if user.user_id in ADMIN_IDS and message.text.lower() == ADMIN_PASSWORD:
        password_ok = True
        user_telemetry_pass = telemetry_pass
    else:
        user_telemetry_pass = generate_password_hash(message.text)
        password_ok = user_telemetry_pass == telemetry_pass

    if not password_ok:
        dialog_manager.dialog_data["incorrect_password"] = True
        await dialog_manager.show(show_mode=ShowMode.DELETE_AND_SEND)
        return

    dialog_manager.dialog_data["incorrect_password"] = False

    subscription = next(
        (s for s in user.subscriptions or [] if s.provider_pubkey == pubkey),
        None,
    )
    if subscription is not None:
        user.subscriptions.remove(subscription)

    user.subscriptions.append(
        UserSubscriptionModel(
            user_id=user.id,
            provider_pubkey=pubkey,
            telemetry_pass=user_telemetry_pass,
        )
    )
    await uow.session.flush()
    await delete_message(message)

    await dialog_manager.start(
        state=states.ProviderMenu.MAIN,
        show_mode=ShowMode.DELETE_AND_SEND,
        data={"provider_pubkey": pubkey},
    )


async def default_message(
    message: Message,
    dialog_manager: DialogManager,
    uow: UnitOfWork,
) -> None:
    pubkey = (
        message.text.strip().lower()
        if message.content_type == ContentType.TEXT
        else None
    )

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

    await delete_message(message)
