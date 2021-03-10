import argparse


class ParseDict(argparse.Action):
    """Parse a KEY=VALUE string-list into a dictionary"""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values,
        *args
    ):
        """Perform the parsing"""
        result = {}

        if values:
            for item in values:
                key, value = item.split("=", 1)
                result[key] = value

        setattr(namespace, self.dest, result)


def parse_args():
    """Parse CLI arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=argparse.FileType("r"), required=True)
    parser.add_argument(
        "--vars",
        dest="vars",
        action=ParseDict,
        nargs="+",
        help="A list of variable structures that specify input parameters. "
        "Syntax: ParameterKey1=ParameterValue1 ParameterKey2=ParameterValue2",
        metavar="ParameterKey=ParameterValue",
        default=dict(),
    )
    parser.add_argument("--stack-name", required=True)

    return parser.parse_args()
