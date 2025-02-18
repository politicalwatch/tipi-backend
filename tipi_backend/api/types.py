from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class VotingOutlier:
    reference: str
    title: str
    group_votes: List[Dict[str, Any]]
