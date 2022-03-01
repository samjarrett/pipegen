import logging
import sys
from io import StringIO, TextIOWrapper
from typing import TYPE_CHECKING, Dict

import boto3
import click
from cfn_sync import Stack
from strictyaml.ruamel import YAML

from . import VERSION
from .args import CONFIG_OPTION, VARS_OPTION
from .config import parse_config
from .generators import generate

if TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_cloudformation.client import CloudFormationClient
else:
    CloudFormationClient = object


def dump_yaml(template, output=sys.stdout):
    """Dumps YAML out to output file"""
    yaml = YAML()
    yaml.indent(sequence=4, offset=2)
    yaml.dump(template, output)


def print_version(ctx, _, value):
    """Output the version of pipegen"""
    if not value or ctx.resilient_parsing:
        return

    click.echo(VERSION)
    ctx.exit()


@click.group()
@click.option(
    "--version", is_flag=True, callback=print_version, expose_value=False, is_eager=True
)
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

    output = StringIO()
    dump_yaml({"Resources": generate(config)}, output)
    template = output.getvalue()

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
    dump_yaml(config)


@dump.command(name="template")
@CONFIG_OPTION
@VARS_OPTION
def dump_template(config_file: TextIOWrapper, var_overrides: Dict[str, str]):
    """Dump the compiled configuration"""
    config = parse_config(config_file.read(), var_overrides)
    dump_yaml({"Resources": generate(config)})


if __name__ == "__main__":
    cli()
