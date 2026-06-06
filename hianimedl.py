import yt_dlp
import time
from typing import List
from argparse import ArgumentParser
from os import path, curdir, makedirs
from webHandler import webHandler

if __name__ == "__main__":
    arguments = ArgumentParser()
    arguments.add_argument(
        "-u",
        "--url",
        help="The Url of the hianime show page.",
        required=True,
    )
    arguments.add_argument(
        "-d",
        "--domain",
        help="The base domain to use.",
        required=False,
        default="https://animex.one",
    )
    arguments.add_argument(
        "-sub",
        "--subbed",
        help="Download the dubbed version of the show.",
        action="store_true",
        required=False,
    )
    arguments.add_argument(
        "-e",
        "--episodes",
        help="Specify episodes to download, all by default. -e 2 3 4 5 6 7 8...",
        type=int,
        default=[0],
        nargs="+",
        required=False,
    )
    arguments.add_argument(
        "-dir",
        "--save_directory",
        help="The directory that the video files are saved to, default is the CWD.",
        default=curdir,
    )
    arguments.add_argument(
        "-ffmpeg",
        "--ffmpeg_location",
        help="The path to the ffmpeg binary to use.",
        default=path.abspath(path.expanduser("~/.local/share/vdhcoapp/ffmpeg")),
    )
    arguments.add_argument(
        "-j",
        "--jelly_format",
        help="Name the downloaded videos with the jelly format. Sx e.g S1, S2",
    )
    arguments.add_argument(
        "-s",
        "--video_service",
        help="The 'data-value' tag of the service to use.",
    )
    arguments.add_argument(
        "-ff",
        "--firefox",
        help="The path to the firefox profile to use.",
        required=True
    )
    args = arguments.parse_args()
    url = args.url
    domain = args.domain
    subbed = args.subbed
    episodes = args.episodes if not 0 in args.episodes else None
    save_directory = args.save_directory
    ffmpeg_location = args.ffmpeg_location
    jelly_format = args.jelly_format
    firefox = args.firefox
    Handler = webHandler

    if domain == "https://animex.one":
        from animex import AnimaxHandler
        Handler = AnimaxHandler
    elif domain == "https://anikototv.to":
        from anikoto import AnikotoHandler
        Handler = AnikotoHandler

    web_handler = Handler(firefox_profile=firefox)
    with web_handler as web:
        if args.video_service:
            web.video_service = args.video_service
        web.downloadShow(url=url, episodes_to_download=episodes, use_jelly=jelly_format, save_dir=save_directory, subbed=subbed)
