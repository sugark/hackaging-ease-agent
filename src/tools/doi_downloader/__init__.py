"""
DOI Downloader Tool - Budapest Hackathlon

A tool for downloading academic papers using DOI identifiers.
Utilizes scidownl library for Sci-Hub access.
"""

from .doi_downloader import DOIDownloader, DownloadResult

__all__ = ["DOIDownloader", "DownloadResult"]
__version__ = "1.0.0"