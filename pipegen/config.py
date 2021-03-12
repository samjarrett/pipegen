import re
from typing import Any, Dict, List, Tuple, TypedDict, Union

import yaml
from jinja2 import Environment, StrictUndefined

REPO_REGEX = (
    r"(?P<account>[\d]{12}).dkr.ecr.(?P<region>[a-z]{2}-[a-z]+-[\d]+)."
    r"amazonaws.com/(?P<repository_name>[a-z0-9\-\/]+)(?:\:(?P<tag>.+))?"
)

# {"Ref": key}
Ref = TypedDict("Ref", {"Ref": str})
# {"Fn::GetAtt": [resource, key]}
FnGetAtt = TypedDict("FnGetAtt", {"Fn::GetAtt": List[str]})
# {"Fn::ImportValue": key}
FnImportValue = TypedDict("FnImportValue", {"Fn::ImportValue": str})
# { "Fn::Sub" : [ String, { Var1Name: Var1Value, Var2Name: Var2Value } ] }
FnSub = Dict[str, Tuple[str, Dict[str, Union[str, Dict[str, str]]]]]


def parse_config(config: str, config_vars: Dict[str, str]) -> Dict[str, Any]:
    """Parse a config and return a Dictionary of the data"""
    environment = Environment(undefined=StrictUndefined)
    template = environment.from_string(config)
    rendered_config = template.render(vars=config_vars)

    return yaml.load(rendered_config, Loader=yaml.SafeLoader)


def parse_value(template: str, **kwargs) -> Union[str, FnSub, Ref]:
    """Create s Fn::Sub reference to a value of various types"""
    if len(kwargs) == 1:
        key = list(kwargs.keys())[0]
        value = kwargs[key]
        # check if our template exactly matches "${Key}"
        if template == f"${{{key}}}":
            if value.startswith("AWS::"):
                return {"Ref": value}
            if not value.startswith("import:"):
                return value

    subbed_args = {}

    for key, value in kwargs.items():
        if value.startswith("import:"):
            value = {"Fn::ImportValue": value[7:]}
        subbed_args[key] = value

    return {"Fn::Sub": (template, subbed_args)}


# From: {account}.dkr.ecr.{region}.amazonaws.com/{repository_name}:{tag}
# To: arn:aws:ecr:{region}:{account}:repository/{repository_name}
def get_ecr_arn(repo_uri: str) -> str:
    """Convert an ECR Repo URI to an ECR Repo ARN"""
    match = re.search(REPO_REGEX, repo_uri)
    if not match:
        raise RuntimeError("URI provided doesn't appear to be an ECR URI")

    return f"arn:aws:ecr:{match['region']}:{match['account']}:repository/{match['repository_name']}"


def codecommit_git_https_uri(source_config: Dict[str, Union[str, bool]]) -> FnSub:
    """Convert source config dict to a git URI"""
    return parse_value(
        "https://git-codecommit.${Region}.amazonaws.com/v1/repos/${RepositoryName}",
        Region=source_config.get("region", "AWS::Region"),
        RepositoryName=source_config.get("repository"),
    )  # type: ignore
