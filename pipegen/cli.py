import logging
from io import TextIOWrapper
from typing import TYPE_CHECKING, Dict

import boto3
import click
import yaml
from cfn_sync import Stack

from .args import CONFIG_OPTION, VARS_OPTION
from .config import parse_config
from .generators import generate

if TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_cloudformation.client import CloudFormationClient
else:
    CloudFormationClient = object


class NoAliasDumper(yaml.SafeDumper):  # pylint: disable=too-many-ancestors
    """A yaml SafeDumper that doesn't use anchors"""

    def ignore_aliases(self, data):
        return True


@click.group()
def cli():
    """pipegen: CodePipeline/CodeBuild stack generator"""
    logging.basicConfig(
        datefmt="%Y-%m-%d %H:%M", format="[%(asctime)s] %(levelname)-2s: %(message)s"
    )


@cli.command()
@CONFIG_OPTION
@VARS_OPTION
@click.option("--stack-name", type=str, required=True)
def deploy(config_file: TextIOWrapper, var_overrides: Dict[str, str], stack_name: str):
    """Deploy CodePipeline stack"""
    config = parse_config(config_file.read(), var_overrides)

    template = yaml.dump({"Resources": generate(config)}, Dumper=NoAliasDumper)

    cloudformation: CloudFormationClient = boto3.client("cloudformation")
    stack = Stack(cloudformation, stack_name)
    stack.set_capabilities(["CAPABILITY_IAM"])
    stack.deploy(template, {}, {})


@cli.group()
def dump():
    """Dump out compiled data"""


@dump.command(name="config")
@CONFIG_OPTION
@VARS_OPTION
def dump_config(config_file: TextIOWrapper, var_overrides: Dict[str, str]):
    """Dump the compiled configuration"""
    config = parse_config(config_file.read(), var_overrides)
    print(yaml.dump(config, Dumper=NoAliasDumper))


@dump.command(name="template")
@CONFIG_OPTION
@VARS_OPTION
def dump_template(config_file: TextIOWrapper, var_overrides: Dict[str, str]):
    """Dump the compiled configuration"""
    config = parse_config(config_file.read(), var_overrides)
    template = yaml.dump({"Resources": generate(config)}, Dumper=NoAliasDumper)
    print(template)


if __name__ == "__main__":
    cli()
