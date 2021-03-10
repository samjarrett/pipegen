from typing import Any, NamedTuple


class ResourceOutput(NamedTuple):
    """A CloudFormation Resource's output"""

    definition: dict[str, Any]
    logical_id: str
