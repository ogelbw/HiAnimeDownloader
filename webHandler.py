import time
from os import makedirs, path
from seleniumwire import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import bs4
import yt_dlp
from typing import List


class webHandler:
    driver: webdriver.Firefox = None
    waiter: WebDriverWait = None
    timeout: int = None

    def __init__(
        self,
        firefox_profile,
        timeout: int = 10,
        ffmpeg_location=None,
    ):
        selenium_options = Options()
        selenium_options.add_argument("--allow-downgrade")
        selenium_options.add_argument("-profile")
        selenium_options.add_argument(firefox_profile)
        selenium_options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0")
        selenium_options.set_preference("dom.webdriver.enabled", False)
        selenium_options.set_preference("useAutomationExtension", False)

        self.driver = webdriver.UndetectedFirefox(options=selenium_options)
        self.waiter = WebDriverWait(self.driver, 5)
        self.timeout = timeout
        self.ffmpeg_location = ffmpeg_location
        # if self.ffmpeg_location is None:
        #     Exception("FFMPEG Location is not provided")

    def __enter__(self):
        return self

    def __exit__(self, _, __, ___):
        self.driver.quit()

    def _waitForPageLoaded(self):
        pass

    def _wait_for_m3u8(self, streams: set):
        start = time.time()
        target_url = None
        target_headers = None
        print("started search for streams")

        # reloading the page to make sure we have the right stream
        del self.driver.requests
        self.driver.refresh()
        self._waitForPageLoaded()

        time.sleep(1)
        while (time.time() - start) < self.timeout:
            # iterate through captured requests
            for request in reversed(self.driver.requests):
                url = request.url

                if url in streams:
                    continue

                headers = dict(request.headers)
                # Check if it's an HLS stream playlist (most likely for this site)
                is_m3u8 = '.m3u8' in url

                # Generic video fallback
                is_video_dest = (headers.get('Sec-Fetch-Dest') == 'video'
                            or headers.get('sec-fetch-dest'  == 'video'))
                is_video_type = ('video/' in headers.get('Accept', '')
                            or 'video/' in headers.get('accept', ''))

                if is_m3u8 or is_video_dest or is_video_type:
                    target_url = url
                    target_headers = headers
                    streams.add(url)
                    break

            if target_url:
                print(f"[Capture] Got Video Stream: {target_url}")
                return (target_url, target_headers)
            time.sleep(1)

    def _downloadEpisode(
        self, url: str, save_dir: str, dub: bool, title: str, streams: set
    ):
        print("[Downloader] Downloading", url)
        self.driver.get(url)
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
            "ffmpeg_location": self.ffmpeg_location,
            "external_downloader": "ffmpeg",
            "format_sort": [
                "res:1080",
                "quality",
                "codec:h264",
                "size",
            ],
            # Selenium-wire and yt-dlp might conflict on certificates,
            "nocheckcertificate": True,
            "paths": {"home": save_dir},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_stream_url])

    def downloadShow(
        self,
        url: str,
        episodes_to_download: None | List[int] = None,
        use_jelly: str = "",
        save_dir=".",
        subbed=False
    ):
        """Download specified episoded from the page at [url]"""
        self.driver.get(url)
        self.waiter.until(EC.presence_of_element_located(
            (By.CLASS_NAME, "ep-item")))
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

        if not path.exists(save_dir):
            makedirs(save_dir, exist_ok=True)

        seen_streams = set()
        for ep in episodes:
            self._downloadEpisode(
                f"{domain}{ep[0]}",
                save_dir=save_dir,
                dub=not subbed,
                title=ep[2],
                streams=seen_streams,
            )