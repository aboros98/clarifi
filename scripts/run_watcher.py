"""Run the file watcher daemon.
Usage: python -m scripts.run_watcher
"""

import asyncio
import logging

from clarifi.discovery.watcher import watch_directory

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(watch_directory())
