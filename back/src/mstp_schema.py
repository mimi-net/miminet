"""MSTP schema types."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class MstInstance:
    """MST (Multiple Spanning Tree) instance configuration."""

    instance_id: int
    vlans: list[int]
    priority: Optional[int] = None
