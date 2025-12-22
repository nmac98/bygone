import ulid

def new_ulid() -> str:
    return ulid.new().str