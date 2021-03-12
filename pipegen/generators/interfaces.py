from typing import Any, Dict, NamedTuple


class ResourceOutput(NamedTuple):
    """A CloudFormation Resource's output"""

    definition: Dict[str, Any]
    logical_id: str
