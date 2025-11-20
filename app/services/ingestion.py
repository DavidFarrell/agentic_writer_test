"""Resource ingestion service.

Per spec section 6.2, handles:
- File uploads (txt, md, pdf, docx, html, json, images, video, audio)
- URL fetching (web pages, YouTube)
- Text extraction
- Tokenization
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, Tuple
import httpx
from bs4 import BeautifulSoup
import google.generativeai as genai
from app.config import Config
from app.services.tokenization import count_tokens
from app.models import Resource, ResourceChunk
from sqlalchemy.orm import Session


class IngestionService:
    """Service for ingesting resources from various sources."""

    def __init__(self):
        self.files_path = Path(Config.FILES_PATH)
        self.files_path.mkdir(parents=True, exist_ok=True)

    def _save_file(self, content: bytes, filename: str) -> str:
        """Save file to storage and return path.

        Args:
            content: File content bytes
            filename: Original filename

        Returns:
            Relative path to saved file
        """
        # Create a unique filename using hash
        file_hash = hashlib.md5(content).hexdigest()[:8]
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{file_hash}{ext}"

        file_path = self.files_path / unique_filename
        file_path.write_bytes(content)

        return str(file_path.relative_to(Config.STORAGE_PATH))

    def extract_text_from_file(self, file_path: Path, file_type: str) -> str:
        """Extract text content from various file types.

        Args:
            file_path: Path to file
            file_type: File extension (e.g., 'txt', 'pdf', 'docx')

        Returns:
            Extracted text
        """
        file_type = file_type.lower().lstrip('.')

        try:
            if file_type in ['txt', 'md', 'json', 'html']:
                return file_path.read_text(encoding='utf-8')

            elif file_type == 'pdf':
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(file_path))
                    text = []
                    for page in reader.pages:
                        text.append(page.extract_text())
                    return '\n\n'.join(text)
                except Exception as e:
                    return f"[PDF extraction failed: {e}]"

            elif file_type == 'docx':
                try:
                    from docx import Document
                    doc = Document(str(file_path))
                    text = []
                    for para in doc.paragraphs:
                        text.append(para.text)
                    return '\n\n'.join(text)
                except Exception as e:
                    return f"[DOCX extraction failed: {e}]"

            elif file_type in ['png', 'jpg', 'jpeg', 'webp', 'gif']:
                # For images, use Gemini vision to extract text/description
                return self._extract_from_image(file_path)

            elif file_type in ['mp4', 'mov', 'avi', 'webm']:
                # For videos, use Gemini to extract transcript
                return self._extract_from_video(file_path)

            elif file_type in ['mp3', 'wav', 'm4a', 'ogg']:
                # For audio, use Gemini to transcribe
                return self._extract_from_audio(file_path)

            else:
                return f"[Unsupported file type: {file_type}]"

        except Exception as e:
            return f"[Error extracting text: {e}]"

    def _extract_from_image(self, file_path: Path) -> str:
        """Extract text/description from image using Gemini.

        Args:
            file_path: Path to image file

        Returns:
            Extracted text/description
        """
        try:
            # Upload file to Gemini
            uploaded_file = genai.upload_file(str(file_path))

            # Use vision model to describe the image
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content([
                "Describe this image in detail. If there is text in the image, transcribe it exactly.",
                uploaded_file
            ])

            return response.text

        except Exception as e:
            return f"[Image processing failed: {e}]"

    def _extract_from_video(self, file_path: Path) -> str:
        """Extract transcript from video using Gemini.

        Args:
            file_path: Path to video file

        Returns:
            Transcript
        """
        try:
            # Upload file to Gemini
            uploaded_file = genai.upload_file(str(file_path))

            # Use multimodal model to transcribe
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content([
                "Please provide a detailed transcript of this video, including all spoken words and important visual content.",
                uploaded_file
            ])

            return response.text

        except Exception as e:
            return f"[Video processing failed: {e}]"

    def _extract_from_audio(self, file_path: Path) -> str:
        """Extract transcript from audio using Gemini.

        Args:
            file_path: Path to audio file

        Returns:
            Transcript
        """
        try:
            # Upload file to Gemini
            uploaded_file = genai.upload_file(str(file_path))

            # Use model to transcribe
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content([
                "Please transcribe this audio file exactly, including all spoken words.",
                uploaded_file
            ])

            return response.text

        except Exception as e:
            return f"[Audio processing failed: {e}]"

    async def fetch_url_content(self, url: str) -> Tuple[str, str]:
        """Fetch and extract content from URL.

        Args:
            url: URL to fetch

        Returns:
            Tuple of (title, content_markdown)
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract title
                title_tag = soup.find('title')
                title = title_tag.get_text() if title_tag else url

                # Remove script and style elements
                for script in soup(['script', 'style']):
                    script.decompose()

                # Get main content
                # Try to find main content area
                main_content = soup.find('main') or soup.find('article') or soup.find('body')

                if main_content:
                    text = main_content.get_text(separator='\n', strip=True)
                else:
                    text = soup.get_text(separator='\n', strip=True)

                # Clean up whitespace
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                content = '\n\n'.join(lines)

                return title, content

        except Exception as e:
            return url, f"[Failed to fetch URL: {e}]"

    async def fetch_youtube_transcript(self, url: str) -> Tuple[str, str]:
        """Fetch YouTube video transcript.

        Args:
            url: YouTube URL

        Returns:
            Tuple of (title, transcript)
        """
        try:
            # Extract video ID
            from urllib.parse import urlparse, parse_qs

            parsed = urlparse(url)
            if 'youtube.com' in parsed.netloc:
                video_id = parse_qs(parsed.query).get('v', [None])[0]
            elif 'youtu.be' in parsed.netloc:
                video_id = parsed.path.lstrip('/')
            else:
                return url, "[Invalid YouTube URL]"

            if not video_id:
                return url, "[Could not extract video ID]"

            # Use Gemini to get transcript from video URL
            # First, try to use YouTube API or yt-dlp, fallback to Gemini
            try:
                # Try using pytube for metadata
                from pytube import YouTube
                yt = YouTube(url)
                title = yt.title

                # For transcript, we'll use Gemini multimodal
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = f"""Please provide a detailed transcript of the YouTube video at: {url}

Extract all spoken words as accurately as possible. Format as a clean transcript."""

                response = model.generate_content(prompt)
                transcript = response.text

                return title, transcript

            except Exception as e:
                # Fallback: just use title from URL
                return f"YouTube: {video_id}", f"[Transcript extraction failed: {e}]"

        except Exception as e:
            return url, f"[YouTube processing failed: {e}]"

    def ingest_file(
        self,
        db: Session,
        project_id: int,
        file_content: bytes,
        filename: str,
        label: str,
        resource_type: str,
        model_id: str
    ) -> Resource:
        """Ingest a file upload.

        Args:
            db: Database session
            project_id: Project ID
            file_content: File content bytes
            filename: Original filename
            label: User-facing label
            resource_type: Resource type (audio_notes, source_transcript, etc.)
            model_id: Model ID for tokenization

        Returns:
            Created Resource object
        """
        # Save file
        file_path = self._save_file(file_content, filename)
        full_path = Path(Config.STORAGE_PATH) / file_path

        # Extract text
        file_type = Path(filename).suffix.lstrip('.')
        text_content = self.extract_text_from_file(full_path, file_type)

        # Count tokens
        token_count = count_tokens(text_content, model_id)

        # Create resource
        resource = Resource(
            project_id=project_id,
            label=label,
            type=resource_type,
            origin="file_upload",
            raw_path=file_path,
            text_content=text_content,
            total_tokens=token_count,
            model_id=model_id,
            active=True
        )

        db.add(resource)
        db.commit()
        db.refresh(resource)

        # Check if chunking needed
        max_tokens = Config.CHUNK_SIZE_TOKENS
        if token_count > max_tokens:
            self._create_chunks(db, resource, text_content, model_id, max_tokens)

        return resource

    async def ingest_url(
        self,
        db: Session,
        project_id: int,
        url: str,
        label: Optional[str],
        resource_type: str,
        model_id: str
    ) -> Resource:
        """Ingest a URL.

        Args:
            db: Database session
            project_id: Project ID
            url: URL to fetch
            label: Optional user-facing label
            resource_type: Resource type
            model_id: Model ID for tokenization

        Returns:
            Created Resource object
        """
        # Determine if YouTube
        is_youtube = 'youtube.com' in url or 'youtu.be' in url

        if is_youtube:
            title, content = await self.fetch_youtube_transcript(url)
        else:
            title, content = await self.fetch_url_content(url)

        # Use provided label or fallback to title
        final_label = label or title

        # Count tokens
        token_count = count_tokens(content, model_id)

        # Create resource
        resource = Resource(
            project_id=project_id,
            label=final_label,
            type=resource_type,
            origin="youtube" if is_youtube else "url",
            url=url,
            text_content=content,
            total_tokens=token_count,
            model_id=model_id,
            active=True
        )

        db.add(resource)
        db.commit()
        db.refresh(resource)

        # Check if chunking needed
        max_tokens = Config.CHUNK_SIZE_TOKENS
        if token_count > max_tokens:
            self._create_chunks(db, resource, content, model_id, max_tokens)

        return resource

    def _create_chunks(
        self,
        db: Session,
        resource: Resource,
        text: str,
        model_id: str,
        chunk_size: int
    ):
        """Create chunks for oversized resources.

        Args:
            db: Database session
            resource: Resource to chunk
            text: Full text content
            model_id: Model ID for tokenization
            chunk_size: Target chunk size in tokens
        """
        # Simple chunking by paragraphs
        paragraphs = text.split('\n\n')

        current_chunk = []
        current_tokens = 0
        chunk_index = 0

        for para in paragraphs:
            para_tokens = count_tokens(para, model_id)

            if current_tokens + para_tokens > chunk_size and current_chunk:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk)
                chunk = ResourceChunk(
                    resource_id=resource.id,
                    sequence_index=chunk_index,
                    text=chunk_text,
                    token_count=current_tokens
                )
                db.add(chunk)
                chunk_index += 1

                # Start new chunk
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens

        # Save final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunk = ResourceChunk(
                resource_id=resource.id,
                sequence_index=chunk_index,
                text=chunk_text,
                token_count=current_tokens
            )
            db.add(chunk)

        db.commit()
