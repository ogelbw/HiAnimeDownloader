import yt_dlp
import time
import bs4
from seleniumwire import webdriver
from selenium.webdriver.firefox.options import Options
from typing import List
from argparse import ArgumentParser
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from os import path, curdir


class webHandler:
    driver: webdriver.Firefox = None
    waiter: WebDriverWait = None
    timeout: int = None

    def __init__(
        self,
        firefox_profile,
        timeout: int = 10,
    ):
        selenium_options = Options()
        selenium_options.add_argument("-profile")
        selenium_options.add_argument(firefox_profile)
        self.driver = webdriver.Firefox(options=selenium_options)
        self.waiter = WebDriverWait(self.driver, 5)
        self.timeout = timeout

    def _wait_for_m3u8(self, streams: set):
        start = time.time()
        target_url = None
        target_headers = None

        while (time.time() - start) < self.timeout:
            for request in reversed(self.driver.requests):
                url = request.url

                # Look for the Master/Multi-variant playlist
                if ".m3u8" in url and url not in streams:
                    if "index" not in url:
                        target_url = url
                        target_headers = dict(request.headers)
                        streams.add(url)
                        break

            if target_url:
                print(f"[m3u8 Capture] Got Master Stream: {target_url}")
                return (target_url, target_headers)
            time.sleep(1)

    def _downloadEpisode(
        self, url: str, save_dir: str, dub: bool, title: str, streams: set
    ):
        print("[Downloader] Downloading", url)
        self.driver.get(url)
        del self.driver.requests
        if dub:
            # wait for the dub selection to appear and click the first entry
            self.waiter.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/div[3]/div[3]/div[1]/div/div/div[2]/div[2]/div[2]/div/div[3]/div[2]/div[1]",
                    )
                )
            ).click()
        else:
            # else click the sub
            self.waiter.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/div[3]/div[3]/div[1]/div/div/div[2]/div[2]/div[2]/div/div[2]/div[2]/div[1]",
                    )
                )
            ).click()
        time.sleep(2)
        video_stream_url, headers = self._wait_for_m3u8(streams)
        ydl_opts = {
            "http_headers": headers,
            "format": "bestvideo+bestaudio/best",
            "outtmpl": f"{title}.mkv",
            "concurrent_fragment_downloads": 5,
            "hls_prefer_native": False,
            "ffmpeg_location": ffmpeg_location,
            "external_downloader": "ffmpeg",
            "format_sort": [
                "res:1080",
                "quality",
                "codec:h264",
                "size",
            ],
            # Selenium-wire and yt-dlp might conflict on certificates,
            "nocheckcertificate": True,
            "paths": {"home": save_directory},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_stream_url])

    def downloadShow(
        self,
        url: str,
        episodes_to_download: None | List[int] = None,
        use_jelly: str = "",
    ):
        self.driver.get(url)
        self.waiter.until(EC.presence_of_element_located((By.CLASS_NAME, "ep-item")))
        rawHTML = self.driver.page_source
        webpage = bs4.BeautifulSoup(rawHTML, "html.parser")

        episodes = [
            (
                ep.get("href"),
                epnum := int(ep.get("data-number")),
                (
                    f"{epnum} {ep.get('title')}"
                    if use_jelly == ""
                    else f"{use_jelly}E{epnum}"
                ),
            )
            for ep in webpage.find_all(class_="ep-item")
        ]

        if episodes_to_download:
            episodes = [
                x for x in filter(lambda ep: ep[1] in episodes_to_download, episodes)
            ]
        episodes.sort(key=lambda x: x[1])

        seen_streams = set()
        for ep in episodes:
            self._downloadEpisode(
                f"{domain}{ep[0]}",
                save_dir=save_directory,
                dub=not subbed,
                title=ep[2],
                streams=seen_streams,
            )

    def __del__(self):
        self.driver.quit()


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
        default="https://hianime.to",
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
        help="Specify episodes to download, all by default.",
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

    web_handler = webHandler(firefox_profile=firefox)
    web_handler.downloadShow(url, episodes_to_download=episodes, use_jelly=jelly_format)
