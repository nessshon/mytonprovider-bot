from __future__ import annotations

import logging
import typing as t
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from ...api.toncenter import ToncenterClient, Transaction
from ...config import TIMEZONE
from ...context import Context
from ...database.helpers import round_to_hour
from ...database.models import WalletHistoryModel, WalletModel
from ...database.unitofwork import UnitOfWork

logger = logging.getLogger(__name__)


@dataclass
class WalletMetrics:
    transfer_in: int = 0
    transfer_out: int = 0
    reward_received: int = 0
    proof_paid: int = 0
    revenue_fees: int = 0
    other_fees: int = 0

    def add(self, metric: WalletMetrics) -> None:
        self.transfer_in += metric.transfer_in
        self.transfer_out += metric.transfer_out
        self.reward_received += metric.reward_received
        self.proof_paid += metric.proof_paid
        self.revenue_fees += metric.revenue_fees
        self.other_fees += metric.other_fees

    @property
    def earned(self) -> int:
        return self.reward_received - self.proof_paid - self.revenue_fees

    @property
    def balance(self) -> int:
        return self.transfer_in + self.earned - self.transfer_out - self.other_fees


async def collect_transactions(
    toncenter: ToncenterClient,
    address: str,
    from_lt: t.Optional[int] = None,
) -> list[Transaction]:
    limit, result = 100, []

    async with toncenter:
        while True:
            response = await toncenter.transactions(
                account=address,
                start_lt=from_lt,
                limit=limit,
                sort="asc",
            )
            transactions = response.transactions
            if not transactions:
                break

            result.extend(
                transaction
                for transaction in transactions
                if from_lt is None or transaction.lt > from_lt
            )
            from_lt = transactions[-1].lt
            if len(transactions) < limit:
                break

    return result


def group_transactions_by_hour(
    transactions: t.List[Transaction],
) -> t.Dict[datetime, t.List[Transaction]]:
    transactions_by_hour: t.Dict[datetime, list[Transaction]] = defaultdict(list)

    for transaction in sorted(transactions, key=lambda tx: tx.now):
        tx_datatime = datetime.fromtimestamp(transaction.now, tz=TIMEZONE)
        tx_datetime_by_hour = round_to_hour(tx_datatime)
        transactions_by_hour[tx_datetime_by_hour].append(transaction)
    return transactions_by_hour


def extract_transaction_metrics(tx: Transaction) -> WalletMetrics:
    total_fees = tx.total_fees or 0
    is_reward_received = False
    has_proof_payment = False
    metrics = WalletMetrics()

    if tx.in_msg and tx.in_msg.value:
        if tx.in_msg.opcode == "0xa91baf56":  # reward withdrawal
            metrics.reward_received = tx.in_msg.value
            is_reward_received = True
        else:
            metrics.transfer_in = tx.in_msg.value

    for msg in tx.out_msgs or []:
        if msg.opcode == "0x48f548ce":  # proof storage
            metrics.proof_paid += msg.value
            has_proof_payment = True
        else:
            metrics.transfer_out += msg.value

        if msg.fwd_fee:
            if has_proof_payment or is_reward_received:
                metrics.revenue_fees += msg.fwd_fee
            else:
                metrics.other_fees += msg.fwd_fee

    if is_reward_received or has_proof_payment:
        metrics.revenue_fees += total_fees
    else:
        metrics.other_fees += total_fees

    return metrics


async def update_wallets_job(ctx: Context) -> None:
    uow = UnitOfWork(ctx.db.session_factory)

    async with uow:
        providers = await uow.provider.all()

    for provider in providers:
        wallet_history_models = []

        async with uow:
            last_wallet = await uow.wallet.get(provider_pubkey=provider.pubkey)

        last_wallet_lt = last_wallet.last_lt if last_wallet else None
        last_wallet_balance = last_wallet.balance if last_wallet else 0
        last_wallet_earned = last_wallet.earned if last_wallet else 0

        transactions = await collect_transactions(
            toncenter=ctx.toncenter,
            address=provider.address,
            from_lt=last_wallet_lt,
        )
        if transactions is None:
            continue

        grouped_transactions = group_transactions_by_hour(transactions)
        for tx_datetime_hour, transactions_in_hour in sorted(
            grouped_transactions.items()
        ):
            wallet_metrics = WalletMetrics()
            for transaction in transactions_in_hour:
                wallet_metrics.add(extract_transaction_metrics(transaction))

            last_wallet_lt = max(tx.lt for tx in transactions_in_hour)
            last_wallet_balance += wallet_metrics.balance
            last_wallet_earned += wallet_metrics.earned

            async with uow:
                last_wallet_history = await uow.wallet_history.get(
                    provider_pubkey=provider.pubkey,
                    archived_at=tx_datetime_hour,
                )

            if last_wallet_history is not None:
                last_wallet_history.earned += wallet_metrics.earned
                last_wallet_history.balance = last_wallet_balance
                last_wallet_history.last_lt = last_wallet_lt
                wallet_history_models.append(last_wallet_history)
            else:
                wallet_history_models.append(
                    WalletHistoryModel(
                        provider_pubkey=provider.pubkey,
                        earned=wallet_metrics.earned,
                        archived_at=tx_datetime_hour,
                        address=provider.address,
                        balance=last_wallet_balance,
                        last_lt=last_wallet_lt,
                    )
                )

        wallet_model = WalletModel(
            provider_pubkey=provider.pubkey,
            address=provider.address,
            balance=last_wallet_balance,
            earned=last_wallet_earned,
            last_lt=last_wallet_lt,
        )

        async with uow:
            await uow.wallet.upsert(wallet_model)
            await uow.wallet_history.bulk_upsert(wallet_history_models)
