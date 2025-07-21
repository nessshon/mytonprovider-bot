from redis.asyncio import Redis

from .telemetry_history import create_telemetry_snapshot
from ...database import UnitOfWork
from ...database.models import TelemetryModel
from ...utils.mtpapi import MyTONProviderAPI


async def sync_telemetry(
    uow: UnitOfWork,
    redis: Redis,
    mtpapi: MyTONProviderAPI,
) -> None:
    response = await mtpapi.telemetry()
    for entry in response.providers:
        telemetry = TelemetryModel(
            provider_pubkey=entry.storage.provider.pubkey.lower(),
            storage_pubkey=entry.storage.pubkey.lower(),
            storage_disk_name=entry.storage.disk_name,
            storage_used_disk_space=entry.storage.used_disk_space,
            storage_total_disk_space=entry.storage.total_disk_space,
            provider_used_provider_space=entry.storage.provider.used_provider_space,
            provider_total_provider_space=entry.storage.provider.total_provider_space,
            ram_total=entry.ram.total if entry.ram else 0,
            ram_usage=entry.ram.usage if entry.ram else 0,
            ram_usage_percent=entry.ram.usage_percent if entry.ram else 0,
            cpu_count=entry.cpu_info.cpu_count if entry.cpu_info else 0,
            cpu_name=entry.cpu_info.cpu_name if entry.cpu_info else "",
            cpu_is_virtual=(entry.cpu_info.is_virtual if entry.cpu_info else False),
            cpu_load=entry.cpu_info.cpu_load if entry.cpu_info else [],
            net_load=entry.net_load or [],
            net_pps=entry.pps or [],
            net_pings=entry.pings or {},
            net_x_real_ip=entry.x_real_ip,
            disk_iops=entry.iops or {},
            disk_load_percent=entry.disks_load_percent or {},
            system_sysname=entry.uname.sysname if entry.uname else "",
            system_release=entry.uname.release if entry.uname else "",
            system_version=entry.uname.version if entry.uname else "",
            system_machine=entry.uname.machine if entry.uname else "",
            raw=entry.model_dump(),
        )

        await uow.telemetry.upsert(telemetry)
        await create_telemetry_snapshot(redis, telemetry)
