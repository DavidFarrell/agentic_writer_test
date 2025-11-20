import os
from pathlib import Path
from typing import Tuple
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

UPLOAD_DIR = Path("agentic_writer/static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class IngestionService:
    def save_upload(self, file_obj, filename: str) -> str:
        path = UPLOAD_DIR / filename
        with open(path, "wb") as f:
            f.write(file_obj.read())
        return str(path)

    def extract_text(self, path: str, file_type: str) -> str:
        path_obj = Path(path)
        if file_type == "application/pdf" or path_obj.suffix.lower() == ".pdf":
            return self._extract_pdf(path)
        else:
            # Assume text/markdown for now
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                return "Error: Could not decode text file."

    def _extract_pdf(self, path: str) -> str:
        try:
            reader = PdfReader(path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            return f"Error extracting PDF: {str(e)}"

    def process_url(self, url: str) -> Tuple[str, str, str]:
        # Returns (title, content, type)
        parsed = urlparse(url)
        if "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc:
            return self._process_youtube(url)
        else:
            return self._process_webpage(url)

    def _process_youtube(self, url: str) -> Tuple[str, str, str]:
        try:
            video_id = self._get_youtube_id(url)
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join([t['text'] for t in transcript])
            return f"YouTube: {video_id}", text, "youtube"
        except Exception as e:
            return "YouTube Video", f"Error fetching transcript: {str(e)}", "youtube"

    def _get_youtube_id(self, url: str) -> str:
        parsed = urlparse(url)
        if "youtu.be" in parsed.netloc:
            return parsed.path[1:]
        if "youtube.com" in parsed.netloc:
            return parse_qs(parsed.query)['v'][0]
        return ""

    def _process_webpage(self, url: str) -> Tuple[str, str, str]:
        try:
            resp = requests.get(url)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            text = soup.get_text()
            # Break into lines and remove leading/trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            title = soup.title.string if soup.title else url
            return title, text, "webpage"
        except Exception as e:
            return url, f"Error fetching URL: {str(e)}", "webpage"
