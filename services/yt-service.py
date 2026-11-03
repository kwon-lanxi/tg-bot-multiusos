from youtube_transcript_api import YouTubeTranscriptApi 
from youtube_transcript_api.proxies import WebshareProxyConfig
from youtube_transcript_api.formatters import JSONFormatter, TextFormatter, SRTFormatter, WebVTTFormatter
from typing import Literal
import yt_dlp
import os

class YTService:
    def __init__(self, proxy_url: str, proxy_username: str, proxy_password: str):
        self.ytt_api  =  YouTubeTranscriptApi ( 
        proxy_config = WebshareProxyConfig ( 
        proxy_username = proxy_username , 
        proxy_password = proxy_password , 
        filter_ip_locations = [ "de" ,  "us" ], 
    ))
        self.ydl_opts_base = {
            'proxy': proxy_url,
            'quiet': True,
            'no_warnings': True
        }
    def download_video(self, url: str, output_path: str) -> str:
        ydl_opts = self.ydl_opts_base.copy()
        ydl_opts.update({
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'format': 'bestvideo+bestaudio/best',
        })
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_title = info_dict.get('title', None)
            video_ext = info_dict.get('ext', None)
            return os.path.join(output_path, f"{video_title}.{video_ext}")
    
    def download_audio(self, url: str, output_path: str) -> str:
        ydl_opts = self.ydl_opts_base.copy()
        ydl_opts.update({
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_title = info_dict.get('title', None)
            return os.path.join(output_path, f"{video_title}.mp3")
        
    def get_metadata(self, url: str) -> dict:
        ydl_opts = self.ydl_opts_base.copy()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            return {
                'title': info_dict.get('title', None),
                'description': info_dict.get('description', None),
                'thumbnail': info_dict.get('thumbnail', None),
                'uploader': info_dict.get('uploader', None),
                'upload_date': info_dict.get('upload_date', None),
                'duration': info_dict.get('duration', None),
                'tags': info_dict.get('tags', []),
            }
    
    def get_transcript(self, video_id: str, format: Literal["json", "text", "srt", "webvtt"] = "text"):
        formatter_map = {
            "json": JSONFormatter(),
            "text": TextFormatter(),
            "srt": SRTFormatter(),
            "webvtt": WebVTTFormatter()
        }
        transcript_list = self.ytt_api.fetch(video_id, languages=["es", "en", "ko"])
        return formatter_map.get(format, TextFormatter()).format(transcript_list)
    
    def get_formatted_download_formats(self, url: str) -> list[dict]:
        ydl_opts = self.ydl_opts_base.copy()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            return info_dict.get('formats', [])