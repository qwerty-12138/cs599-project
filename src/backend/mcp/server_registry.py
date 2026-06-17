"""MCP server configuration registry"""
import json
import os
import uuid
import time
import logging
from typing import Optional
from .config import MCPServerConfig

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data")
REGISTRY_FILE = os.path.join(DATA_DIR, "mcp_servers.json")


class ServerRegistry:
    """Persists MCP server configurations in-memory with JSON file backup."""

    def __init__(self):
        self._servers: dict[str, MCPServerConfig] = {}
        self._load()

    def _load(self):
        if os.path.exists(REGISTRY_FILE):
            try:
                with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        config = MCPServerConfig(**item)
                        self._servers[config.id] = config
                logger.info(f"Loaded {len(self._servers)} MCP servers from registry")
            except Exception as e:
                logger.warning(f"Failed to load registry: {e}")

    def _save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        try:
            data = [s.dict() for s in self._servers.values()]
            with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save registry: {e}")

    def add_server(self, config: MCPServerConfig):
        self._servers[config.id] = config
        self._save()

    def update_server(self, server_id: str, updates: dict):
        if server_id in self._servers:
            server = self._servers[server_id]
            for key, value in updates.items():
                if hasattr(server, key):
                    setattr(server, key, value)
            self._save()

    def remove_server(self, server_id: str):
        self._servers.pop(server_id, None)
        self._save()

    def get_server(self, server_id: str) -> Optional[MCPServerConfig]:
        return self._servers.get(server_id)

    def get_servers(self) -> list[MCPServerConfig]:
        return list(self._servers.values())

    def get_enabled_servers(self) -> list[MCPServerConfig]:
        return [s for s in self._servers.values() if s.enabled]


server_registry = ServerRegistry()


# Seed some demo servers
def seed_demo_servers():
    pass


seed_demo_servers()
