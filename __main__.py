import logging
from utils.logging_setup import setup_logger
setup_logger(log_to_file=True)
from bot import main
import asyncio
import asyncpg
import os

import shutil

source_folder = "/data"
zip_path = "/data/data_backup.zip"

# This will zip everything inside /data into data_backup.zip
shutil.make_archive(zip_path.replace(".zip", ""), 'zip', source_folder)

from flask import Flask, send_from_directory

app = Flask(__name__)
UPLOAD_FOLDER = "/data"

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)



logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.debug("This should appear in both terminal and file.")
    from pathlib import Path

    path = Path("/data")  # Replace with your actual mount path

    if path.exists() and path.is_dir():
        print(f"Contents of {path}:")
        for item in path.iterdir():
            print(item.name)
    else:
        print(f"{path} does not exist or is not a directory.")

    for root, dirs, files in os.walk("/data"):
        print(f"Directory: {root}")
        for name in files:
            print(f"  File: {name}")
        for name in dirs:
            print(f"  Sub-directory: {name}")


    asyncio.run(main())
