from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MstInstance:
    instance_id: int
    vlans: List[int]
    priority: Optional[int] = None
