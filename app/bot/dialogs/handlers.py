from aiogram.enums import ContentType
from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode

from . import states
from ..utils import generate_passwd_hash, is_valid_pubkey
from ...config import ADMIN_IDS, ADMIN_PASSWORD
from ...database.models import UserModel, UserSubscriptionModel
from ...database.unitofwork import UnitOfWork


async def search_provider(
    message: Message,
    _,
    manager: DialogManager,
) -> None:
    uow: UnitOfWork = manager.middleware_data["uow"]
    pubkey = (
        message.text.strip().lower()
        if message.content_type == ContentType.TEXT
        else None
    )

    if not pubkey or not is_valid_pubkey(pubkey):
        await manager.switch_to(
            states.MainMenu.INVALID_INPUT,
            show_mode=ShowMode.SEND,
        )
    else:
        if await uow.provider.exists(pubkey=pubkey):
            await manager.start(
                state=states.ProviderMenu.MAIN,
                data={"provider_pubkey": pubkey},
                show_mode=ShowMode.SEND,
            )
        else:
            await manager.switch_to(
                states.MainMenu.NOT_FOUND,
                show_mode=ShowMode.SEND,
            )


async def enter_password(
    message: Message,
    _,
    manager: DialogManager,
) -> None:
    if message.content_type != ContentType.TEXT:
        return

    uow: UnitOfWork = manager.middleware_data["uow"]
    user: UserModel = manager.middleware_data["user_model"]
    pubkey = manager.dialog_data.get("provider_pubkey")
    telemetry = await uow.telemetry.get(provider_pubkey=pubkey)
    telemetry_pass = telemetry.telemetry_pass if telemetry else None

    if user.user_id in ADMIN_IDS and message.text.lower() == ADMIN_PASSWORD:
        password_ok = True
        user_telemetry_pass = telemetry_pass
    else:
        user_telemetry_pass = generate_passwd_hash(message.text)
        password_ok = user_telemetry_pass == telemetry_pass

    if not password_ok:
        manager.dialog_data["incorrect_password"] = True
        return

    manager.dialog_data["incorrect_password"] = False

    subscription = next(
        (s for s in user.subscriptions or [] if s.provider_pubkey == pubkey),
        None,
    )
    if subscription is not None:
        subscription.telemetry_pass = user_telemetry_pass
    else:
        user.subscriptions.append(
            UserSubscriptionModel(
                user_id=user.id,
                provider_pubkey=pubkey,
                telemetry_pass=user_telemetry_pass,
            )
        )
    await uow.session.flush()

    await manager.start(
        state=states.ProviderMenu.MAIN,
        show_mode=ShowMode.SEND,
        data={"provider_pubkey": pubkey},
    )


async def search_bag(
    message: Message,
    _,
    manager: DialogManager,
) -> None:
    if message.content_type != ContentType.TEXT:
        return

    uow: UnitOfWork = manager.middleware_data["uow"]
    bag_id = message.text.strip().lower()
    pubkey = manager.dialog_data.get("provider_pubkey")

    if not bag_id or not is_valid_pubkey(bag_id):
        await manager.switch_to(
            states.ProviderMenu.BAGS_NOT_FOUND,
            show_mode=ShowMode.SEND,
        )
        return

    contract = await uow.contract.get(bag_id=bag_id, provider_pubkey=pubkey)
    if not contract:
        await manager.switch_to(
            states.ProviderMenu.BAGS_NOT_FOUND,
            show_mode=ShowMode.SEND,
        )
        return

    manager.dialog_data["contract_address"] = contract.address
    manager.dialog_data["contract_pubkey"] = contract.provider_pubkey
    await manager.switch_to(
        states.ProviderMenu.BAGS_DETAIL,
        show_mode=ShowMode.SEND,
    )
