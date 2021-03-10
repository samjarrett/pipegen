import json
from typing import TYPE_CHECKING
import logging

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


def main():
    """The main entry point"""
    args = parse_args()

    logging.basicConfig(
        datefmt="%Y-%m-%d %H:%M", format="[%(asctime)s] %(levelname)-2s: %(message)s"
    )

    config = parse_config(args.config.read(), args.vars)

    template = yaml.dump(
        json.loads(json.dumps({"Resources": generate(config)})), sort_keys=True
    )

    cloudformation: CloudFormationClient = boto3.client("cloudformation")
    stack = Stack(cloudformation, args.stack_name)
    stack.set_capabilities(["CAPABILITY_IAM"])
    stack.deploy(template, {}, {})


if __name__ == "__main__":
    main()
