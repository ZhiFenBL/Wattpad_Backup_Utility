import argparse
from endpoints import fetch_cookies, fetch_story_content_zip, fetch_library
from epub_generator import EPUBGenerator
from parser import fetch_image, fetch_tree_images, clean_tree
from asyncio import run
from pathlib import Path
from os import remove
from zipfile import ZipFile
from json import load, dump
from re import sub

# This helper function remains unchanged
def ascii_only(string: str):
    string = string.replace(" ", "_")
    return sub(
        r"[^qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890\-\_)(`~.><\[\]{}]",
        "",
        string,
    )

# The core logic is moved into its own async function
async def run_backup(
    username: str, password: str, output_directory: Path, download_images: bool
):
    print("Logging in")
    cookies = await fetch_cookies(username, password)

    print("Fetching library")
    stories = await fetch_library(username, cookies)
    download_history_path = Path(output_directory / "download_history")
    if download_history_path.exists():
        with open(download_history_path, "r") as file:
            download_history = load(file)
    else:
        download_history_path.parent.mkdir(parents=True, exist_ok=True)
        download_history = {}

    print("Downloading missing/outdated stories")

    try:
        for metadata in stories:
            if (
                metadata["title"] in download_history
                and download_history[metadata["title"]] == metadata["modifyDate"]
            ):
                continue

            print(f"Downloading: {metadata['title']}")

            cover_data = await fetch_image(
                metadata["cover"].replace("-256-", "-512-")
            )
            if not cover_data:
                # Handle this error more gracefully if needed
                print(f"Warning: Could not fetch cover for {metadata['title']}")
                continue


            story_zip = await fetch_story_content_zip(metadata["id"], cookies)
            archive = ZipFile(story_zip, "r")
            part_trees = []

            for part in metadata["parts"]:
                if part.get("deleted", False):
                    continue

                part_trees.append(
                    clean_tree(
                        part["title"],
                        part["id"],
                        archive.read(str(part["id"])).decode("utf-8"),
                    )
                )

            images = (
                [await fetch_tree_images(tree) for tree in part_trees]
                if download_images
                else []
            )

            book = EPUBGenerator(metadata, part_trees, cover_data, images)
            book.compile()

            output_path = (
                output_directory
                / ascii_only(metadata["user"]["name"]) # Corrected to 'name' as 'username' is not in the user object
                / ascii_only((metadata["title"] + ".epub"))
            )

            output_path.parent.mkdir(parents=True, exist_ok=True)

            if output_path.exists():
                remove(output_path)
            with open(output_path, "xb") as output:
                output.write(book.dump().getvalue())

            download_history[metadata["title"]] = metadata["modifyDate"]
    finally:
        with open(download_history_path, "w") as file:
            dump(download_history, file)

def main():
    # 1. Set up the argument parser
    parser = argparse.ArgumentParser(description="Wattpad Backup Utility")

    # 2. Define the arguments you want to accept
    parser.add_argument("-u", "--username", type=str, required=True, help="Your Wattpad username.")
    parser.add_argument("-p", "--password", type=str, required=True, help="Your Wattpad password.")
    parser.add_argument("-o", "--output", type=Path, default=Path("./wattpad_backup"), help="The directory to save your EPUB files.")
    parser.add_argument("--use-images", action="store_true", help="Include this flag to download images with the stories.")

    # 3. Parse the arguments from the command line
    args = parser.parse_args()

    # 4. Run your asynchronous backup function with the parsed arguments
    run(
        run_backup(
            username=args.username,
            password=args.password,
            output_directory=args.output,
            download_images=args.use_images,
        )
    )


if __name__ == "__main__":
    main()
