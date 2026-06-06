"""Web downloader for Animax"""
from typing import List
from os import makedirs, path
import re
import yt_dlp
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webHandler import webHandler


class AnikotoHandler(webHandler):
    """Web downloader for AniKoto

    Args:
        webHandler (Selenium Web driver): The selenium webdriver used.
    """

    def __init__(self, firefox_profile, timeout=10, ffmpeg_location=None):
        super().__init__(firefox_profile, timeout, ffmpeg_location)
        self.video_service = None

    def _waitForPageLoaded(self):
        # This waits until the first episode of the list is loaded
        self.waiter.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//*[@id=\"w-episodes\"]"
                )
            )
        )

    def _downloadEpisode(
        self, url: str, save_dir: str, dub: bool, title: str, streams: set
    ):
        """Downloads the episode at [url] and haves it in [save_dir] as [title].
        NOTE: [url] is actually an xpath but is named this for naming consistancy
        """
        print("[Downloader] Downloading", title)

        # Go to the episode
        self.driver.get(url)

        # Load the steam we actually are intrested in by finding the button
        i=0
        stream_tgt_type = "dub" if dub else "sub"
        stream_catagory_container = "/html/body/div[1]/div/div[1]/div/div/aside[1]/div[1]/div[1]/div[3]/div[2]/div"
        while True:
            i += 1
            stream_type = self.waiter.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        stream_catagory_container + f"[{i}]"
                    )
                )
            ).get_attribute("data-type")

            if stream_type == stream_tgt_type:
                stream_catagory_container += f"[{i}]"
                break

        if self.video_service:
            # loop through the options until we hit the service.
            while True:
                service = self.waiter.until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            stream_catagory_container + f"/ul/li[{i}]"
                        )
                    )
                )
                if service.text.lower() == self.video_service.lower():
                    service.click()
        else:
            self.waiter.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        stream_catagory_container + "/ul/li[1]"
                    )
                )
            ).click()
        self._waitForPageLoaded()

        # self.driver.get_cookies()

        # Get the video stream and download it.
        for _ in range(5):
            try:
                video_stream_url, _ = self._wait_for_m3u8(streams)
                break
            except TypeError:
                print("Failed to get stream, trying again")
        else:
            exit(-1)

        ydl_opts = {
            "force_generic_extractor": True,

            # Use a full User-Agent. Some servers reject short ones like "Mozilla/5.0"
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0"
            " Safari/537.36",

            "http_headers": {
                "Referer": "https://anikototv.to",
                "Origin" : "https://anikototv.to",
                "Accept" : "*/*",
            },

            "format": "bestvideo+bestaudio/best",
            "outtmpl": f"{title}.mkv",
            "nocheckcertificate": True,
            "paths": {"home": save_dir},
            "hls_prefer_native": True,
            "external_downloader_args": {
                "ffmpeg": [
                    "-allowed_extensions", "ALL",
                    "-protocol_whitelist", "file,http,https,tcp,tls,crypto"
                ]
            },
            "legacy_server_connect": True,
            "format_sort": ["res:1080", "quality", "codec:h264", "size"],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_stream_url])

    def downloadShow(
        self,
        url: str,
        episodes_to_download: None | List[int] = None,
        use_jelly: str = "",
        save_dir=".",
        subbed=False,
    ):
        """Download specified episoded from the page at [url]"""

        show_page_indicator = (
            By.XPATH,
            r'//*[@id="w-episodes"]'
        )

        # Goto the show page
        print("Going to", url)
        self.driver.get(url)
        print("Waiting for episodes to load")
        self.waiter.until(EC.presence_of_element_located(show_page_indicator))

        def episodes_gen():
            print("Generating episode list")
            # /html/body/div[1]/div/div[1]/div/div/aside[1]/div[1]/div[2]/div[2]/div/ul
            # data-range="001-009"
            # https://anikototv.to/watch/kill-blue-gcqj5/ep-1
            url_base = "/".join(url.split("/")[:-1])
            data_range =[int(ep) for ep in re.findall(r'\d{3}',self.waiter.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        r'/html/body/div[1]/div/div[1]/div/div/aside[1]/div[1]/div[2]/div[2]/div/ul'
                    )
                )
            ).get_attribute("data-range"))]

            for ep_num in range(data_range[0], data_range[1]):
                yield {
                        "url"   : f"{url_base}/ep-{ep_num}",
                        "ep_num": ep_num,
                        "ep_title": f"Episode {ep_num}"
                    }

        episodes = list(episodes_gen())
        if episodes_to_download:
            episodes = [
                x for x in filter(lambda ep: ep["ep_num"] in episodes_to_download, episodes)
            ]
        episodes.sort(key=lambda x: x["ep_num"])

        print("Begining show download.")
        seen_streams: set[str] = set()
        for ep in episodes:
            self._downloadEpisode(
                url=ep["url"],
                save_dir=save_dir,
                dub=not subbed,
                title=ep["ep_title"],
                streams=seen_streams,
            )

        if not path.exists(save_dir):
            makedirs(save_dir, exist_ok=True)
