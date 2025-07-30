from __future__ import annotations

import logging
import typing as t
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, date

from ...config import TIMEZONE
from ...context import Context
from ...database import UnitOfWork
from ...database.models.provider import ProviderWalletHistoryModel
from ...utils.toncenter import TONCenterAPI
from ...utils.toncenter.models import Transaction

logger = logging.getLogger(__name__)

PROOF_STORAGE_OPCODE = "0x48f548ce"
REWARD_WITHDRAWAL_OPCODE = "0xa91baf56"


@dataclass
class WalletMetrics:
    transfer_in: int = 0
    transfer_out: int = 0

    reward_received: int = 0
    proof_paid: int = 0
    revenue_fees: int = 0
    other_fees: int = 0

    def add(self, other: WalletMetrics) -> None:
        self.transfer_in += other.transfer_in
        self.transfer_out += other.transfer_out
        self.reward_received += other.reward_received
        self.proof_paid += other.proof_paid
        self.revenue_fees += other.revenue_fees
        self.other_fees += other.other_fees

    @property
    def earned(self) -> int:
        return self.reward_received - self.proof_paid - self.revenue_fees

    @property
    def balance(self) -> int:
        return self.transfer_in + self.earned - self.transfer_out - self.other_fees


async def collect_transactions(
    toncenterapi: TONCenterAPI,
    address: str,
    from_lt: t.Optional[int] = None,
) -> list[Transaction]:
    limit = 100
    result: list[Transaction] = []

    while True:
        response = await toncenterapi.transactions(
            account=address,
            limit=limit,
            sort="asc",
            start_lt=from_lt,
        )
        transactions = response.transactions
        if not transactions:
            break

        result.extend(tx for tx in transactions if from_lt is None or tx.lt > from_lt)
        from_lt = transactions[-1].lt

        if len(transactions) < limit:
            break

    return result


def extract_tx_metrics(tx: Transaction) -> WalletMetrics:
    total_fees = tx.total_fees or 0
    is_reward_received = False
    has_proof_payment = False
    metrics = WalletMetrics()

    if tx.in_msg and tx.in_msg.value:
        if tx.in_msg.opcode == REWARD_WITHDRAWAL_OPCODE:
            metrics.reward_received = tx.in_msg.value
            is_reward_received = True
        else:
            metrics.transfer_in = tx.in_msg.value

    for msg in tx.out_msgs or []:
        if msg.opcode == PROOF_STORAGE_OPCODE:
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


async def monitor_balances_job(ctx: Context) -> None:
    uow = UnitOfWork(ctx.db.session_factory)
    toncenterapi: TONCenterAPI = ctx.toncenterapi

    async with uow:
        providers = await uow.provider.all()

        for provider in providers:
            last_record = await uow.provider_wallet_history.get(
                provider_pubkey=provider.pubkey,
                order_by=ProviderWalletHistoryModel.last_lt.desc(),
            )

            from_lt = last_record.last_lt if last_record else None
            previous_balance = last_record.balance if last_record else 0

            try:
                async with toncenterapi:
                    transactions = await collect_transactions(
                        toncenterapi=toncenterapi,
                        address=provider.address,
                        from_lt=from_lt,
                    )
            except Exception:
                logger.exception(
                    f"Failed to collect transactions for {provider.pubkey}"
                )
                raise

            if not transactions:
                continue

            logger.info(
                f"Retrieved {len(transactions)} new transactions for {provider.pubkey} "
                f"from_lt {from_lt}"
            )

            transactions_by_date: dict[date, list[Transaction]] = defaultdict(list)
            for tx in transactions:
                tx_date = datetime.fromtimestamp(tx.now, tz=TIMEZONE).date()
                transactions_by_date[tx_date].append(tx)

            for tx_date in sorted(transactions_by_date):
                metrics = WalletMetrics()
                txs = transactions_by_date[tx_date]
                for tx in txs:
                    metrics.add(extract_tx_metrics(tx))

                last_lt_for_day = max(tx.lt for tx in txs)
                previous_balance += metrics.balance
                updated_at = datetime.now(TIMEZONE)

                logger.info(
                    f"Provider {provider.pubkey}, date {tx_date}, "
                    f"earned {metrics.earned / 1e9:.9f}, balance {previous_balance / 1e9:.9f}, txs {len(txs)}"
                )

                existing = await uow.provider_wallet_history.get(
                    provider_pubkey=provider.pubkey,
                    date=tx_date,
                )
                if existing:
                    existing.updated_at = updated_at
                    existing.balance = previous_balance
                    existing.earned += metrics.earned
                    existing.last_lt = last_lt_for_day
                    await uow.provider_wallet_history.upsert(existing)
                else:
                    model = ProviderWalletHistoryModel(
                        provider_pubkey=provider.pubkey,
                        date=tx_date,
                        address=provider.address,
                        updated_at=updated_at,
                        balance=previous_balance,
                        earned=metrics.earned,
                        last_lt=last_lt_for_day,
                    )
                    await uow.provider_wallet_history.upsert(model)
