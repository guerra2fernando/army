"""
Document Chunking Service
Splits documents into smaller chunks for embedding.
"""
from typing import List, Dict, Any
import re


class TextChunker:
    """
    Splits documents into smaller chunks for embedding.
    Uses recursive character text splitting.
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
    
    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            metadata: Metadata to attach to each chunk
            
        Returns:
            List of chunk dictionaries with content and metadata
        """
        if not text:
            return []
        
        chunks = self._split_text(text)
        
        # Filter out empty chunks
        chunks = [c for c in chunks if c.strip()]
        
        if not chunks:
            return []
        
        result = []
        for i, chunk in enumerate(chunks):
            chunk_data = {
                "content": chunk,
                "metadata": {
                    **(metadata or {}),
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            }
            result.append(chunk_data)
        
        return result
    
    def _split_text(self, text: str) -> List[str]:
        """Split text using recursive character splitting."""
        return self._split_recursive(text, self.separators)
    
    def _split_recursive(
        self,
        text: str,
        separators: List[str]
    ) -> List[str]:
        """Recursively split text by separators."""
        
        if not text:
            return []
        
        if not separators:
            return [text]
        
        separator = separators[0]
        remaining_separators = separators[1:]
        
        if separator:
            splits = text.split(separator)
        else:
            # Character-level split
            splits = list(text)
        
        chunks = []
        current_chunk = ""
        
        for split in splits:
            test_chunk = current_chunk + (separator if current_chunk else "") + split
            
            if len(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                if len(split) > self.chunk_size:
                    # Recursively split large pieces
                    sub_chunks = self._split_recursive(split, remaining_separators)
                    if sub_chunks:
                        chunks.extend(sub_chunks[:-1])
                        current_chunk = sub_chunks[-1]
                    else:
                        current_chunk = ""
                else:
                    current_chunk = split
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # Add overlap
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)
        
        return chunks
    
    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """Add overlapping content between chunks."""
        if len(chunks) <= 1:
            return chunks
        
        result = [chunks[0]]
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]
            
            # Get overlap from previous chunk
            if len(prev_chunk) > self.chunk_overlap:
                overlap = prev_chunk[-self.chunk_overlap:]
            else:
                overlap = prev_chunk
            
            # Prepend overlap to current chunk
            result.append(overlap + " " + current_chunk)
        
        return result


class MarkdownChunker(TextChunker):
    """
    Specialized chunker for Markdown documents.
    Preserves section structure where possible.
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "]
        )
    
    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Split markdown preserving section headers.
        """
        if not text:
            return []
        
        # Extract headers for context
        headers = re.findall(r'^#{1,3}\s+(.+)$', text, re.MULTILINE)
        
        chunks = super().chunk_text(text, metadata)
        
        # Enhance metadata with detected headers
        for chunk in chunks:
            chunk["metadata"]["headers"] = headers
        
        return chunks

