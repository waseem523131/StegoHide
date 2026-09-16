"""Interactive menu for StegoHide."""

import os
import sys
from pathlib import Path
import ctypes

from cli.commands import main as cli_main
from reports.report_manager import (
    list_reports,
    open_report,
    delete_report,
)


# ============================================================
# Windows / Terminal Colors
# ============================================================

class Colors:
    RESET = "\033[0m"

    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    DIM = "\033[2m"


def enable_windows_colors():
    """Enable ANSI colors in Windows terminals."""
    if os.name != "nt":
        return

    if not sys.stdout.isatty():
        return

    try:
        

        kernel32 = ctypes.windll.kernel32

        handle = kernel32.GetStdHandle(-11)

        mode = ctypes.c_ulong()

        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

            kernel32.SetConsoleMode(
                handle,
                mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING,
            )

    except Exception:
        pass


enable_windows_colors()


# ============================================================
# Project Paths
# ============================================================

WIDTH = 50

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"


# ============================================================
# Helper Functions
# ============================================================

def color(text, color_code):
    """Return colored text."""
    return f"{color_code}{text}{Colors.RESET}"


def line(char="-", line_color=Colors.CYAN):
    """Print a colored horizontal line."""
    print(
        color(
            "+" + char * WIDTH + "+",
            line_color,
        )
    )


def header(title_text):
    """Print a section header."""
    print()

    line()

    print(
        "|"
        + color(
            title_text.center(WIDTH),
            Colors.BRIGHT_CYAN,
        )
        + "|"
    )

    line()


def pause():
    """Wait before returning to the main menu."""
    input(
        "\n"
        + color(
            "Press ENTER to return to the main menu...",
            Colors.DIM,
        )
    )


def ensure_directories():
    """Create required project directories."""
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_images(directory):
    """Return PNG and BMP images from a directory."""
    ensure_directories()

    return sorted(
        [
            path
            for path in directory.iterdir()
            if path.is_file()
            and path.suffix.lower() in {".png", ".bmp"}
        ],
        key=lambda path: path.name.lower(),
    )


def select_image(directory, title_text):
    """Display available images and select one by number."""

    images = get_images(directory)

    if not images:
        header("NO IMAGES FOUND")

        print()

        print(
            color(
                "No PNG or BMP images were found in:",
                Colors.YELLOW,
            )
        )

        print(
            color(
                str(directory),
                Colors.DIM,
            )
        )

        pause()
        return None

    print()

    print(
        color(
            title_text,
            Colors.BRIGHT_WHITE,
        )
    )

    print(
        color(
            "-" * WIDTH,
            Colors.DIM,
        )
    )

    for index, image in enumerate(images, start=1):

        number = color(
            f"[{index}]",
            Colors.BRIGHT_YELLOW,
        )

        name = color(
            f"  {image.name}",
            Colors.WHITE,
        )

        print(f"{number}{name}")

    print(
        color(
            "-" * WIDTH,
            Colors.DIM,
        )
    )

    while True:

        choice = input(
            "\n"
            + color(
                "Select image: ",
                Colors.BRIGHT_CYAN,
            )
            + "> "
        ).strip()

        try:
            number = int(choice)

            if 1 <= number <= len(images):
                return images[number - 1]

            print(
                color(
                    f"\nInvalid selection. "
                    f"Choose a number from 1 to {len(images)}.",
                    Colors.BRIGHT_RED,
                )
            )

        except ValueError:

            print(
                color(
                    "\nInvalid input. Please enter a number.",
                    Colors.BRIGHT_RED,
                )
            )

def select_file(directory, title, extensions):
    
    files = sorted(
        [
            path
            for path in directory.iterdir()
            if path.is_file()
            and path.suffix.lower() in extensions
        ]
    )

    if not files:

        print(
            color(
                f"\nNo files found in {directory}.",
                Colors.BRIGHT_YELLOW,
            )
        )

        pause()
        return None

    print()

    line()

    print(
        "|"
        + color(
            title.center(WIDTH),
            Colors.BRIGHT_WHITE,
        )
        + "|"
    )

    line()

    for index, file_path in enumerate(files, start=1):

        print(
            color(
                f"[{index}] ",
                Colors.BRIGHT_CYAN,
            )
            + file_path.name
        )

    print()

    choice = input(
        color(
            "Select file number: ",
            Colors.BRIGHT_CYAN,
        )
    ).strip()

    if not choice.isdigit():

        print(
            color(
                "\nERROR: Invalid selection.",
                Colors.BRIGHT_RED,
            )
        )

        pause()
        return None

    index = int(choice)

    if index < 1 or index > len(files):

        print(
            color(
                "\nERROR: Selection out of range.",
                Colors.BRIGHT_RED,
            )
        )

        pause()
        return None

    return files[index - 1]

def run_command(arguments):
    """Run an existing StegoHide CLI command."""

    try:
        return cli_main(arguments)

    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1


# ============================================================
# Hide Text
# ============================================================

def hide_menu():

    header("HIDE TEXT")

    input_image = select_image(
        INPUT_DIR,
        "Available Input Images",
    )

    if input_image is None:
        return

    print()

    print(
        color(
            "Output File Name",
            Colors.BRIGHT_WHITE,
        )
    )

    output_name = input(
        color("> ", Colors.BRIGHT_CYAN)
    ).strip()

    if not output_name:

        print(
            color(
                "\nERROR: Output file name cannot be empty.",
                Colors.BRIGHT_RED,
            )
        )

        pause()
        return

    output_path = OUTPUT_DIR / output_name

    if output_path.suffix.lower() not in {".png", ".bmp"}:

        print(
            color(
                "\nERROR: Output file must be PNG or BMP.",
                Colors.BRIGHT_RED,
            )
        )

        pause()
        return

    if output_path.exists():

        print()

        print(
            color(
                f"WARNING: {output_path.name} already exists.",
                Colors.BRIGHT_YELLOW,
            )
        )

        confirmation = input(
            color(
                "Overwrite it? (y/n): ",
                Colors.BRIGHT_CYAN,
            )
        ).strip().lower()

        if confirmation != "y":

            print(
                color(
                    "\nOperation cancelled.",
                    Colors.YELLOW,
                )
            )

            pause()
            return

    print()

    print(
        color(
            "Message",
            Colors.BRIGHT_WHITE,
        )
    )

    message = input(
        color("> ", Colors.BRIGHT_CYAN)
    )

    print()

    line()

    print(
        "|"
        + color(
            "PROCESSING".center(WIDTH),
            Colors.BRIGHT_YELLOW,
        )
        + "|"
    )

    line()

    exit_code = run_command(
        [
            "hide",
            str(input_image),
            str(output_path),
            "--message",
            message,
        ]
    )

    if exit_code == 0:

        print()

        print(
            color(
                "SUCCESS: Message hidden successfully.",
                Colors.BRIGHT_GREEN,
            )
        )

    pause()
    
def docx_hide_menu():
    
    header("HIDE TEXT IN DOCX")

    input_docx = select_file(
        INPUT_DIR,
        "Available Input DOCX Files",
        {".docx"},
    )

    if input_docx is None:
        return

    print()

    print(
        color(
            "Output File Name",
            Colors.BRIGHT_WHITE,
        )
    )

    output_name = input(
        color("> ", Colors.BRIGHT_CYAN)
    ).strip()

    if not output_name:

        print(
            color(
                "\nERROR: Output file name cannot be empty.",
                Colors.BRIGHT_RED,
            )
        )

        pause()
        return

    output_path = OUTPUT_DIR / output_name

    if output_path.suffix.lower() != ".docx":

        print(
            color(
                "\nERROR: Output file must be DOCX.",
                Colors.BRIGHT_RED,
            )
        )

        pause()
        return

    if output_path.exists():

        print()

        print(
            color(
                f"WARNING: {output_path.name} already exists.",
                Colors.BRIGHT_YELLOW,
            )
        )

        confirmation = input(
            color(
                "Overwrite it? (y/n): ",
                Colors.BRIGHT_CYAN,
            )
        ).strip().lower()

        if confirmation != "y":

            print(
                color(
                    "\nOperation cancelled.",
                    Colors.YELLOW,
                )
            )

            pause()
            return

    print()

    print(
        color(
            "Message",
            Colors.BRIGHT_WHITE,
        )
    )

    message = input(
        color("> ", Colors.BRIGHT_CYAN)
    )

    print()

    line()

    print(
        "|"
        + color(
            "PROCESSING".center(WIDTH),
            Colors.BRIGHT_YELLOW,
        )
        + "|"
    )

    line()

    exit_code = run_command(
        [
            "docx-hide",
            str(input_docx),
            str(output_path),
            "--message",
            message,
        ]
    )

    if exit_code == 0:

        print()

        print(
            color(
                "SUCCESS: Message hidden in DOCX successfully.",
                Colors.BRIGHT_GREEN,
            )
        )

    pause()


# ============================================================
# Extract Text
# ============================================================

def extract_menu():

    header("EXTRACT TEXT")

    stego_image = select_image(
        OUTPUT_DIR,
        "Available Stego Images",
    )

    if stego_image is None:
        return

    print()

    line()

    print(
        "|"
        + color(
            "PROCESSING".center(WIDTH),
            Colors.BRIGHT_YELLOW,
        )
        + "|"
    )

    line()

    exit_code = run_command(
        [
            "extract",
            str(stego_image),
        ]
    )

    if exit_code == 0:

        print()

        print(
            color(
                "SUCCESS: Message extracted successfully.",
                Colors.BRIGHT_GREEN,
            )
        )

    pause()

def docx_extract_menu():
    
    header("EXTRACT TEXT FROM DOCX")

    input_docx = select_file(
        OUTPUT_DIR,
        "Available Stego DOCX Files",
        {".docx"},
    )

    if input_docx is None:
        return

    print()

    line()

    print(
        "|"
        + color(
            "PROCESSING".center(WIDTH),
            Colors.BRIGHT_YELLOW,
        )
        + "|"
    )

    line()

    exit_code = run_command(
        [
            "docx-extract",
            str(input_docx),
        ]
    )

    if exit_code == 0:

        print()

        print(
            color(
                "SUCCESS: Message extracted from DOCX successfully.",
                Colors.BRIGHT_GREEN,
            )
        )

    pause()

# ============================================================
# Image Capacity
# ============================================================

def capacity_menu():

    header("IMAGE CAPACITY")

    image = select_image(
        INPUT_DIR,
        "Available Input Images",
    )

    if image is None:
        return

    print()

    line()

    print(
        "|"
        + color(
            "CAPACITY INFORMATION".center(WIDTH),
            Colors.BRIGHT_YELLOW,
        )
        + "|"
    )

    line()

    exit_code = run_command(
        [
            "capacity",
            str(image),
        ]
    )

    if exit_code == 0:

        print()

        print(
            color(
                "Capacity check completed successfully.",
                Colors.BRIGHT_GREEN,
            )
        )

    pause()


def capacity_menu():

    header("IMAGE CAPACITY")

    image = select_image(
        INPUT_DIR,
        "Available Input Images",
    )

    if image is None:
        return

    print()

    line()

    print(
        "|"
        + color(
            "CAPACITY INFORMATION".center(WIDTH),
            Colors.BRIGHT_YELLOW,
        )
        + "|"
    )

    line()

    exit_code = run_command(
        [
            "capacity",
            str(image),
        ]
    )

    if exit_code == 0:

        print()

        print(
            color(
                "Capacity check completed successfully.",
                Colors.BRIGHT_GREEN,
            )
        )

    pause()



# ============================================================
# List Reports
# ============================================================

def reports_list_menu():

    header("LIST REPORTS")

    reports = list_reports()

    if not reports:

        print(
            color(
                "\nNo reports found.",
                Colors.YELLOW,
            )
        )

        pause()
        return

    print()

    print(
        color(
            "Available Reports",
            Colors.BRIGHT_WHITE,
        )
    )

    print(
        color(
            "-" * WIDTH,
            Colors.DIM,
        )
    )

    for index, report_name in enumerate(reports, start=1):

        number = color(
            f"[{index}]",
            Colors.BRIGHT_YELLOW,
        )

        name = color(
            f"  {report_name}",
            Colors.WHITE,
        )

        print(f"{number}{name}")

    print(
        color(
            "-" * WIDTH,
            Colors.DIM,
        )
    )

    print(
        color(
            f"Total reports: {len(reports)}",
            Colors.BRIGHT_CYAN,
        )
    )

    pause()


# ============================================================
# View Report
# ============================================================

def view_report_menu():

    header("VIEW PREVIOUS REPORT")

    reports = list_reports()

    if not reports:

        print(
            color(
                "\nNo reports found.",
                Colors.YELLOW,
            )
        )

        pause()
        return

    print()

    print(
        color(
            "Available Reports",
            Colors.BRIGHT_WHITE,
        )
    )

    print(
        color(
            "-" * WIDTH,
            Colors.DIM,
        )
    )

    for index, report_name in enumerate(reports, start=1):

        number = color(
            f"[{index}]",
            Colors.BRIGHT_YELLOW,
        )

        name = color(
            f"  {report_name}",
            Colors.WHITE,
        )

        print(f"{number}{name}")

    print(
        color(
            "-" * WIDTH,
            Colors.DIM,
        )
    )

    while True:

        choice = input(
            "\n"
            + color(
                "Select report: ",
                Colors.BRIGHT_CYAN,
            )
            + "> "
        ).strip()

        try:

            number = int(choice)

            if 1 <= number <= len(reports):
                break

            print(
                color(
                    f"\nInvalid selection. "
                    f"Choose a number from 1 to {len(reports)}.",
                    Colors.BRIGHT_RED,
                )
            )

        except ValueError:

            print(
                color(
                    "\nInvalid input. Please enter a number.",
                    Colors.BRIGHT_RED,
                )
            )

    report_name = reports[number - 1]

    try:

        report_content = open_report(report_name)

        header("REPORT DETAILS")

        print()

        print(
            color(
                report_content,
                Colors.WHITE,
            ),
            end="",
        )

    except Exception as exc:

        header("ERROR")

        print(
            color(
                f"\n{exc}",
                Colors.BRIGHT_RED,
            )
        )

    pause()


# ============================================================
# Delete Report
# ============================================================

def delete_report_menu():

    header("DELETE REPORT")

    reports = list_reports()

    if not reports:

        print(
            color(
                "\nNo reports found.",
                Colors.YELLOW,
            )
        )

        pause()
        return

    print()

    print(
        color(
            "Available Reports",
            Colors.BRIGHT_WHITE,
        )
    )

    print(
        color(
            "-" * WIDTH,
            Colors.DIM,
        )
    )

    for index, report_name in enumerate(reports, start=1):

        number = color(
            f"[{index}]",
            Colors.BRIGHT_YELLOW,
        )

        name = color(
            f"  {report_name}",
            Colors.WHITE,
        )

        print(f"{number}{name}")

    print(
        color(
            "-" * WIDTH,
            Colors.DIM,
        )
    )

    while True:

        choice = input(
            "\n"
            + color(
                "Select report to delete: ",
                Colors.BRIGHT_CYAN,
            )
            + "> "
        ).strip()

        try:

            number = int(choice)

            if 1 <= number <= len(reports):
                break

            print(
                color(
                    f"\nInvalid selection. "
                    f"Choose a number from 1 to {len(reports)}.",
                    Colors.BRIGHT_RED,
                )
            )

        except ValueError:

            print(
                color(
                    "\nInvalid input. Please enter a number.",
                    Colors.BRIGHT_RED,
                )
            )

    report_name = reports[number - 1]

    print()

    confirmation = input(
        color(
            f"Delete '{report_name}'? (y/n): ",
            Colors.BRIGHT_YELLOW,
        )
    ).strip().lower()

    if confirmation != "y":

        print(
            color(
                "\nDeletion cancelled.",
                Colors.YELLOW,
            )
        )

        pause()
        return

    try:

        if delete_report(report_name):

            print(
                color(
                    "\nSUCCESS: Report deleted successfully.",
                    Colors.BRIGHT_GREEN,
                )
            )

        else:

            print(
                color(
                    "\nReport not found.",
                    Colors.BRIGHT_RED,
                )
            )

    except Exception as exc:

        print(
            color(
                f"\nERROR: {exc}",
                Colors.BRIGHT_RED,
            )
        )

    pause()


# ============================================================
# Help
# ============================================================
def help_menu():
    
    header("HELP")

    help_items = [
        ("[1] Hide Text",
         "Hide a UTF-8 message inside a PNG or BMP image."),

        ("[2] Extract Text",
         "Extract a hidden message from a StegoHide image."),

        ("[3] Check Image Capacity",
         "Display image dimensions and available LSB capacity."),

        ("[4] Hide Text in DOCX",
         "Hide a UTF-8 message inside a DOCX document."),

        ("[5] Extract Text from DOCX",
         "Extract a hidden message from a DOCX document."),

        ("[6] Hide Text in Video",
         "Hide a UTF-8 message inside an STV video."),

        ("[7] Extract Text from Video",
         "Extract a hidden message from an STV video."),

        ("[8] Image Forensics",
         "Analyze an image and check for a StegoHide signature."),

        ("[9] View Previous Report",
         "Open a previously generated operation report."),

        ("[10] List Reports",
         "Display all generated reports."),

        ("[11] Delete Report",
         "Delete a selected report."),

        ("[12] Help",
         "Display this help information."),

        ("[0] Exit",
         "Exit StegoHide."),
    ]

    print()

    for option, description in help_items:

        print(
            color(
                option,
                Colors.BRIGHT_YELLOW,
            )
        )

        print(
            color(
                f"    {description}",
                Colors.WHITE,
            )
        )

        print()

    pause()

# ============================================================
# Main Menu
# ============================================================

def main_menu():

    ensure_directories()

    while True:

        print()

        line()

        print(
            "|"
            + color(
                "STEGOHIDE".center(WIDTH),
                Colors.BRIGHT_CYAN,
            )
            + "|"
        )

        print(
            "|"
            + color(
                "Steganography Training Tool".center(WIDTH),
                Colors.WHITE,
            )
            + "|"
        )

        line()

        print(
            "|"
            + " " * WIDTH
            + "|"
        )

        print(
            "|"
            + color(
                "MAIN MENU".center(WIDTH),
                Colors.BRIGHT_CYAN,
            )
            + "|"
        )

        print(
            "|"
            + color(
                "-" * WIDTH,
                Colors.DIM,
            )
            + "|"
        )

        menu_items = [
            "[1]  Hide Text",
            "[2]  Extract Text",
            "[3]  Check Image Capacity",
            "[4]  Hide Text in DOCX",
            "[5]  Extract Text from DOCX",
            "[6]  Hide Text in Video",
            "[7]  Extract Text from Video",
            "[8]  Image Forensics",
            "[9]  View Previous Report",
            "[10] List Reports",
            "[11] Delete Report",
            "[12] Help",
            "[0]  Exit",
        ]

        for item in menu_items:

            option_end = item.find("]") + 1

            option = item[:option_end]
            description = item[option_end:]

            content = (
                "  "
                + color(
                    option,
                    Colors.BRIGHT_YELLOW,
                )
                + color(
                    description,
                    Colors.WHITE,
                )
            )

            visible_length = len(item) + 2

            padding = " " * max(
                0,
                WIDTH - visible_length,
            )

            print(
                "|"
                + content
                + padding
                + "|"
            )

        print(
            "|"
            + " " * WIDTH
            + "|"
        )

        line()

        prompt_text = "  Select an option: >"

        padding = " " * (
            WIDTH - len(prompt_text)
        )

        print(
            "|"
            + color(
                prompt_text,
                Colors.BRIGHT_CYAN,
            )
            + padding
            + "|"
        )

        line()

        choice = input(
            color(
                "> ",
                Colors.BRIGHT_YELLOW,
            )
        ).strip()

        if choice == "1":
            hide_menu()

        elif choice == "2":
            extract_menu()

        elif choice == "3":
            capacity_menu()

        elif choice == "4":
            docx_hide_menu()

        elif choice == "5":
            docx_extract_menu()

        elif choice == "6":
            video_hide_menu()

        elif choice == "7":
            video_extract_menu()
        elif choice == "8":
            forensics_menu()

        elif choice == "9":
            view_report_menu()

        elif choice == "10":
            reports_list_menu()

        elif choice == "11":
            delete_report_menu()

        elif choice == "12":
            help_menu()

        elif choice == "0":
            
            print()

            line()

            print(
                "|"
                + color(
                    "Thank you for using StegoHide.".center(WIDTH),
                    Colors.BRIGHT_GREEN,
                )
                + "|"
            )

            print(
                "|"
                + color(
                    "Goodbye!".center(WIDTH),
                    Colors.WHITE,
                )
                + "|"
            )

            line()

            break

        else:

            header("ERROR")

            print()

            print(
                color(
                    "Invalid option.",
                    Colors.BRIGHT_RED,
                )
            )

            print(
                color(
                    "Please select a number from 0 to 12.",
                    Colors.YELLOW,
                )
            )

            pause()
            
def video_hide_menu():
    
    header("HIDE TEXT IN VIDEO")

    input_video = select_file(
        INPUT_DIR,
        "Available Input STV Files",
        {".stv"},
    )

    if input_video is None:
        return

    print()

    print(
        color(
            "Output File Name",
            Colors.BRIGHT_WHITE,
        )
    )

    output_name = input(
        color("> ", Colors.BRIGHT_CYAN)
    ).strip()

    if not output_name:

        print(
            color(
                "\nERROR: Output file name cannot be empty.",
                Colors.BRIGHT_RED,
            )
        )

        pause()
        return

    output_path = OUTPUT_DIR / output_name

    if output_path.suffix.lower() != ".stv":

        print(
            color(
                "\nERROR: Output file must be STV.",
                Colors.BRIGHT_RED,
            )
        )

        pause()
        return

    if output_path.exists():

        print()

        print(
            color(
                f"WARNING: {output_path.name} already exists.",
                Colors.BRIGHT_YELLOW,
            )
        )

        confirmation = input(
            color(
                "Overwrite it? (y/n): ",
                Colors.BRIGHT_CYAN,
            )
        ).strip().lower()

        if confirmation != "y":

            print(
                color(
                    "\nOperation cancelled.",
                    Colors.YELLOW,
                )
            )

            pause()
            return

    print()

    print(
        color(
            "Message",
            Colors.BRIGHT_WHITE,
        )
    )

    message = input(
        color("> ", Colors.BRIGHT_CYAN)
    )

    print()

    line()

    print(
        "|"
        + color(
            "PROCESSING".center(WIDTH),
            Colors.BRIGHT_YELLOW,
        )
        + "|"
    )

    line()

    exit_code = run_command(
        [
            "video-hide",
            str(input_video),
            str(output_path),
            "--message",
            message,
        ]
    )

    if exit_code == 0:

        print()

        print(
            color(
                "SUCCESS: Message hidden in video successfully.",
                Colors.BRIGHT_GREEN,
            )
        )

    pause()
    
def video_extract_menu():
    
    header("EXTRACT TEXT FROM VIDEO")

    input_video = select_file(
        OUTPUT_DIR,
        "Available Stego STV Files",
        {".stv"},
    )

    if input_video is None:
        return

    print()

    line()

    print(
        "|"
        + color(
            "PROCESSING".center(WIDTH),
            Colors.BRIGHT_YELLOW,
        )
        + "|"
    )

    line()

    exit_code = run_command(
        [
            "video-extract",
            str(input_video),
        ]
    )

    if exit_code == 0:

        print()

        print(
            color(
                "SUCCESS: Message extracted from video successfully.",
                Colors.BRIGHT_GREEN,
            )
        )

    pause()
    
def forensics_menu():
    
    header("IMAGE FORENSICS")

    image = select_image(
        INPUT_DIR,
        "Available Input Images",
    )

    if image is None:
        return

    print()

    line()

    print(
        "|"
        + color(
            "FORENSIC ANALYSIS".center(WIDTH),
            Colors.BRIGHT_YELLOW,
        )
        + "|"
    )

    line()

    exit_code = run_command(
        [
            "forensics",
            str(image),
        ]
    )

    if exit_code == 0:

        print()

        print(
            color(
                "Forensic analysis completed successfully.",
                Colors.BRIGHT_GREEN,
            )
        )

    pause()