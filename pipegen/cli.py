import logging
from typing import TYPE_CHECKING

import boto3
import yaml
from cfn_sync import Stack

from .args import parse_args
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


def main():
    """The main entry point"""
    args = parse_args()

    logging.basicConfig(
        datefmt="%Y-%m-%d %H:%M", format="[%(asctime)s] %(levelname)-2s: %(message)s"
    )

    config = parse_config(args.config.read(), args.vars)

    template = yaml.dump({"Resources": generate(config)}, Dumper=NoAliasDumper)

    cloudformation: CloudFormationClient = boto3.client("cloudformation")
    stack = Stack(cloudformation, args.stack_name)
    stack.set_capabilities(["CAPABILITY_IAM"])
    stack.deploy(template, {}, {})


if __name__ == "__main__":
    main()
