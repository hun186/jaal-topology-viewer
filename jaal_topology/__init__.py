"""Portable directed-CSV Jaal graph adapter; no TextClassification/WorkPool dependency."""

from pathlib import Path

from .data import Graph, GraphInputError, load_graph, select_subgraph
from .gallery import GalleryCase, create_gallery_app

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

__all__ = [
    "Graph", "GraphInputError", "load_graph", "select_subgraph",
    "GalleryCase", "create_gallery_app",
]
