def is_valid_pubkey(pubkey: str) -> bool:
    if len(pubkey) != 64:
        return False
    try:
        bytes.fromhex(pubkey)
        return True
    except ValueError:
        return False
