"""Command-line interface for StegoHide."""

import argparse
from pathlib import Path

from config.config import load_config
from core.embed import embed_message
from core.extract import extract_message
from core.image import read_image_metadata
from core.capacity import check_capacity
from reports.report_manager import (
    create_report,
    delete_report,
    list_reports,
    open_report,
)
from utils.logger import configure_logger


VERSION = "1.0.0"


def build_parser():
    parser = argparse.ArgumentParser(
        prog="StegoHide",
        description=(
            "StegoHide - educational LSB steganography "
            "for PNG and BMP images."
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"StegoHide {VERSION}",
    )

    parser.add_argument(
        "--config",
        help="Path to the JSON configuration file.",
    )

    parser.add_argument(
        "--log-level",
        default=None,
        choices=[
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ],
        help="Set the logging level.",
    )

    subparsers = parser.add_subparsers(
        dest="command"
    )

    # ---------------------------------------------------------
    # HIDE
    # ---------------------------------------------------------

    hide_parser = subparsers.add_parser(
        "hide",
        help="Hide a text message in an image.",
    )

    hide_parser.add_argument(
        "input_pos",
        nargs="?",
        help="Source PNG or BMP image.",
    )

    hide_parser.add_argument(
        "output_pos",
        nargs="?",
        help="Output PNG or BMP image.",
    )

    hide_parser.add_argument(
        "--input",
        dest="input_opt",
        help="Source PNG or BMP image.",
    )

    hide_parser.add_argument(
        "--output",
        dest="output_opt",
        help="Output PNG or BMP image.",
    )

    message_group = hide_parser.add_mutually_exclusive_group(
        required=True
    )

    message_group.add_argument(
        "--message",
        help="UTF-8 text message to hide.",
    )

    message_group.add_argument(
        "--message-file",
        help="UTF-8 text file containing the message to hide.",
    )

    # ---------------------------------------------------------
    # EXTRACT
    # ---------------------------------------------------------

    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract a hidden message from an image.",
    )

    extract_parser.add_argument(
        "input_pos",
        nargs="?",
        help="Stego PNG or BMP image.",
    )

    extract_parser.add_argument(
        "--input",
        dest="input_opt",
        help="Stego PNG or BMP image.",
    )

    extract_parser.add_argument(
        "--output",
        help=(
            "Optional UTF-8 text file to write "
            "the extracted message."
        ),
    )

    # ---------------------------------------------------------
    # CAPACITY
    # ---------------------------------------------------------

    capacity_parser = subparsers.add_parser(
        "capacity",
        help="Show image capacity information.",
    )

    capacity_parser.add_argument(
        "input",
        help="Path to the PNG or BMP image.",
    )

    capacity_parser.add_argument(
        "--message-length",
        type=int,
        help=(
            "Check if a message of this byte length "
            "can fit."
        ),
    )

    # ---------------------------------------------------------
    # REPORTS
    # ---------------------------------------------------------

    reports_parser = subparsers.add_parser(
        "reports",
        help="Manage TXT operation reports.",
    )

    reports_subparsers = reports_parser.add_subparsers(
        dest="reports_command"
    )

    reports_subparsers.add_parser(
        "list",
        help="List generated reports.",
    )

    open_parser = reports_subparsers.add_parser(
        "open",
        help="Display one report.",
    )

    open_parser.add_argument(
        "name",
        help="Report file name.",
    )

    delete_parser = reports_subparsers.add_parser(
        "delete",
        help="Delete one report.",
    )

    delete_parser.add_argument(
        "name",
        help="Report file name.",
    )

    return parser


def _image_details(path):
    """Return basic image information for reports."""
    image = read_image_metadata(path)

    return {
        "Image Name": Path(path).name,
        "Image Width": image["width"],
        "Image Height": image["height"],
        "Pixel Count": (
            image["width"] * image["height"]
        ),
    }


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config(args.config)

    log_level = (
        args.log_level
        or config.get("log_level", "INFO")
    )

    logger = configure_logger(log_level)

    # =========================================================
    # CAPACITY
    # =========================================================

    if args.command == "capacity":
        details = {}

        try:
            details = _image_details(args.input)

            capacity = (
                check_capacity(
                    args.message_length,
                    details["Image Width"],
                    details["Image Height"],
                )
                if args.message_length is not None
                else None
            )

            pixels = details["Pixel Count"]

            capacity_bits = pixels * 3
            capacity_bytes = capacity_bits // 8

            print(f"Image: {args.input}")
            print(
                f"Dimensions: "
                f"{details['Image Width']}x"
                f"{details['Image Height']}"
            )
            print(f"Pixels: {pixels}")
            print(
                f"Capacity: "
                f"{capacity_bits} bits "
                f"({capacity_bytes} bytes)"
            )
            print("Header: 13 bytes (104 bits)")

            if capacity is not None:
                print(
                    f"Message length: "
                    f"{args.message_length} bytes"
                )

                print(
                    f"Required: "
                    f"{capacity['required_bits']} bits"
                )

                print(
                    "Fits: "
                    f"{'yes' if capacity['sufficient'] else 'no'}"
                )

            return 0

        except Exception as exc:
            logger.error(
                "Capacity check failed: %s",
                exc,
            )

            print(f"Error: {exc}")

            return 1

    # =========================================================
    # HIDE
    # =========================================================

    if args.command == "hide":
        details = {}

        try:
            input_path = (
                args.input_opt
                or args.input_pos
            )

            output_path = (
                args.output_opt
                or args.output_pos
            )

            if not input_path or not output_path:
                raise ValueError(
                    "Hide requires input and output image paths."
                )

            if args.message_file:
                message = Path(
                    args.message_file
                ).read_text(
                    encoding="utf-8"
                )
            else:
                message = args.message

            details = _image_details(
                input_path
            )

            result = embed_message(
                message,
                input_path,
                output_path,
            )

            details.update(
                {
                    "Available Capacity": (
                        f"{result['capacity']['capacity_bits']} bits"
                    ),
                    "Message Length": (
                        result["message_length"]
                    ),
                    "Required Capacity": (
                        f"{result['header_size'] * 8 + result['message_length'] * 8} bits"
                    ),
                    "Output Image": (
                        result["output_path"]
                    ),
                }
            )

            report_path = create_report(
                "Hide",
                "Success",
                details,
            )

            print(
                "Message hidden successfully: "
                f"{result['output_path']}"
            )

            print(
                f"Report: {report_path}"
            )

            return 0

        except Exception as exc:
            logger.error(
                "Hide failed: %s",
                exc,
            )

            report_path = create_report(
                "Hide",
                "Failed",
                details,
                str(exc),
            )

            print(f"Error: {exc}")
            print(f"Report: {report_path}")

            return 1

    # =========================================================
    # EXTRACT
    # =========================================================

    if args.command == "extract":
        details = {}

        try:
            input_path = (
                args.input_opt
                or args.input_pos
            )

            if not input_path:
                raise ValueError(
                    "Extract requires an input image path."
                )

            details = _image_details(
                input_path
            )

            result = extract_message(
                input_path
            )

            # Add extracted message information
            # to the report.
            details.update(
                {
                    "Extracted Message Length": (
                        result["message_length"]
                    ),
                    "Extracted Message": (
                        result["message"]
                    ),
                }
            )

            report_path = create_report(
                "Extract",
                "Success",
                details,
            )

            if args.output:
                Path(args.output).write_text(
                    result["message"],
                    encoding="utf-8",
                )

                print(
                    "Extracted message written to: "
                    f"{args.output}"
                )

            else:
                print(
                    "Message extracted successfully:"
                )
                print()
                print(result["message"])

            print(
                f"Report: {report_path}"
            )

            return 0

        except Exception as exc:
            logger.error(
                "Extract failed: %s",
                exc,
            )

            report_path = create_report(
                "Extract",
                "Failed",
                details,
                str(exc),
            )

            print(f"Error: {exc}")
            print(f"Report: {report_path}")

            return 1

    # =========================================================
    # REPORTS
    # =========================================================

    if args.command == "reports":

        if args.reports_command == "list":
            reports = list_reports()

            if not reports:
                print("No reports found.")

            else:
                for name in reports:
                    print(name)

            return 0

        if args.reports_command == "open":
            try:
                print(
                    open_report(args.name),
                    end="",
                )

                return 0

            except Exception as exc:
                print(f"Error: {exc}")

                return 1

        if args.reports_command == "delete":
            try:
                if delete_report(args.name):
                    print(
                        f"Report deleted: "
                        f"{args.name}"
                    )

                    return 0

                print(
                    f"Report not found: "
                    f"{args.name}"
                )

                return 1

            except Exception as exc:
                print(f"Error: {exc}")

                return 1

        print(
            "Usage: python main.py "
            "reports {list,open,delete}"
        )

        return 0

    # =========================================================
    # HELP
    # =========================================================

    parser.print_help()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())