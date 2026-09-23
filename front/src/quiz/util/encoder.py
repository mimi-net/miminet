import json
from uuid import UUID


class UUIDEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, UUID):
            return o.hex

        return json.JSONEncoder.default(self, o)
