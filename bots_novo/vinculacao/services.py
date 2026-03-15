from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import requests

from .config import (
    ALL_TRACKED_ROLE_NAMES,
    BASE_URL,
    DEFAULT_REGION,
    DISCORD_BOT_TOKEN,
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    DISCORD_GUILD_ID,
    DISCORD_REDIRECT_URI,
    HENRIK_API_KEY,
    RANK_ROLE_MAP,
)

print("DISCORD_CLIENT_ID:", DISCORD_CLIENT_ID)
print("DISCORD_REDIRECT_URI:", DISCORD_REDIRECT_URI)
print("BASE_URL:", BASE_URL)

DISCORD_API = "https://discord.com/api/v10"
HENRIK_API = "https://api.henrikdev.xyz/valorant"


class AppError(Exception):
    pass


def build_discord_oauth_url(state: str) -> str:
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": DISCORD_REDIRECT_URI,
        "scope": "identify connections",
        "state": state,
        "prompt": "consent",
    }
    return f"https://discord.com/oauth2/authorize?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict[str, Any]:
    response = requests.post(
        f"{DISCORD_API}/oauth2/token",
        data={
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    if not response.ok:
        raise AppError(f"Não foi possível autenticar com o Discord. Resposta: {response.text}")

    return response.json()


def get_discord_user(access_token: str) -> dict[str, Any]:
    response = requests.get(
        f"{DISCORD_API}/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20,
    )
    if not response.ok:
        raise AppError("Não foi possível buscar sua conta do Discord.")
    return response.json()


def get_discord_connections(access_token: str) -> list[dict[str, Any]]:
    response = requests.get(
        f"{DISCORD_API}/users/@me/connections",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20,
    )
    if not response.ok:
        raise AppError("Não foi possível ler suas conexões do Discord.")
    return response.json()


def extract_riot_from_connections(connections: list[dict[str, Any]]) -> tuple[str, str] | None:
    for connection in connections:
        if connection.get("type") != "riotgames":
            continue
        raw_name = (connection.get("name") or "").strip()
        if "#" in raw_name:
            name, tag = raw_name.split("#", 1)
            if name and tag:
                return name.strip(), tag.strip()
    return None


def validate_riot_id(name: str, tag: str) -> tuple[str, str]:
    name = name.strip()
    tag = tag.strip().upper()
    if not name or not tag:
        raise AppError("Preencha Riot ID e tag corretamente.")
    return name, tag


def henrik_headers() -> dict[str, str]:
    return {"Authorization": HENRIK_API_KEY}


def fetch_account(region: str, name: str, tag: str) -> dict[str, Any]:
    response = requests.get(
        f"{HENRIK_API}/v2/account/{name}/{tag}",
        headers=henrik_headers(),
        timeout=20,
    )
    if not response.ok:
        raise AppError("Não consegui validar essa conta Riot na API do Valorant.")
    return response.json()


def fetch_mmr(region: str, name: str, tag: str) -> dict[str, Any]:
    response = requests.get(
        f"{HENRIK_API}/v3/mmr/{region}/pc/{name}/{tag}",
        headers=henrik_headers(),
        timeout=20,
    )
    if not response.ok:
        raise AppError("Não consegui buscar o elo dessa conta agora.")
    return response.json()


def parse_rank_name(current_data: dict[str, Any]) -> str:
    tier_name = (
        current_data.get("currenttierpatched")
        or current_data.get("tier", {}).get("name")
        or ""
    )

    if not tier_name or tier_name == "Unrated":
        return ""

    base = tier_name.split()[0].strip()
    return base if base in RANK_ROLE_MAP else ""


def assign_rank_roles(discord_user_id: str, rank_name: str) -> None:
    if not DISCORD_BOT_TOKEN or not DISCORD_GUILD_ID:
        raise AppError("Configure DISCORD_BOT_TOKEN e DISCORD_GUILD_ID no .env.")

    guild_roles = requests.get(
        f"{DISCORD_API}/guilds/{DISCORD_GUILD_ID}/roles",
        headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"},
        timeout=20,
    )
    if not guild_roles.ok:
        raise AppError("Não consegui ler os cargos do servidor.")

    roles = guild_roles.json()
    role_map = {role["name"]: role["id"] for role in roles}

    # pega o cargo correspondente ao elo, se existir
    keep_role_name = RANK_ROLE_MAP.get(rank_name)

    # remove todos os cargos de elo antigos
    for role_name in ALL_TRACKED_ROLE_NAMES:
        role_id = role_map.get(role_name)
        if not role_id:
            continue
        if role_name == keep_role_name:
            continue

        requests.delete(
            f"{DISCORD_API}/guilds/{DISCORD_GUILD_ID}/members/{discord_user_id}/roles/{role_id}",
            headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"},
            timeout=20,
        )

    # se não houver elo detectado, só remove os antigos e para
    if not keep_role_name:
        return

    keep_role_id = role_map.get(keep_role_name)
    if not keep_role_id:
        raise AppError(f'O cargo "{keep_role_name}" não existe no servidor.')

    add_response = requests.put(
        f"{DISCORD_API}/guilds/{DISCORD_GUILD_ID}/members/{discord_user_id}/roles/{keep_role_id}",
        headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"},
        timeout=20,
    )
    if add_response.status_code not in (200, 204):
        raise AppError("Não consegui entregar o cargo ao membro. Verifique permissões e hierarquia.")


def remove_rank_roles(discord_user_id: str) -> None:
    if not DISCORD_BOT_TOKEN or not DISCORD_GUILD_ID:
        raise AppError("Configure DISCORD_BOT_TOKEN e DISCORD_GUILD_ID no .env.")

    guild_roles = requests.get(
        f"{DISCORD_API}/guilds/{DISCORD_GUILD_ID}/roles",
        headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"},
        timeout=20,
    )
    if not guild_roles.ok:
        raise AppError("Não consegui ler os cargos do servidor.")

    roles = guild_roles.json()
    role_map = {role["name"]: role["id"] for role in roles}

    for role_name in ALL_TRACKED_ROLE_NAMES:
        role_id = role_map.get(role_name)
        if not role_id:
            continue

        requests.delete(
            f"{DISCORD_API}/guilds/{DISCORD_GUILD_ID}/members/{discord_user_id}/roles/{role_id}",
            headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"},
            timeout=20,
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def random_state() -> str:
    return secrets.token_urlsafe(24)


def get_default_region() -> str:
    return DEFAULT_REGION
