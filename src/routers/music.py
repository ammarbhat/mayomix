from fastapi import Depends, HTTPException, APIRouter
from src.models import User
from typing import Annotated
from src.database import get_db
from typing import Annotated
import httpx
from pydantic import Field
from src.dependencies import (
    genre_tag_string,
    get_current_user,
)
import asyncio
import time

router = APIRouter()


musicbrainz_semaphore = asyncio.Semaphore(1)


async def rate_limited_get(client: httpx.AsyncClient, url: str, **kwargs):
    async with musicbrainz_semaphore:
        start = time.monotonic()
        response = await client.get(url, **kwargs)
        elapsed = time.monotonic() - start
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        return response


@router.get("/search/albums")
async def search_albums_endpoint(
    query: str,
    current: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Field(default=15, lt=25, ge=1)],
    db=Depends(get_db),
):
    user = db.query(User).filter(User.username == current.username).first()
    genre_string = genre_tag_string(user.fav_genres)
    mod_query = f'releasegroup:"{query}" AND ({genre_string}) AND primarytype:album'
    url = "https://musicbrainz.org/ws/2/release-group/"
    params = {"query": mod_query, "fmt": "json", "limit": limit}
    headers = {"User-Agent": "mayo-mix/0.1 (https://github.com/ammarbhat)"}

    async with httpx.AsyncClient() as client:
        response = await rate_limited_get(url, params=params, headers=headers)
        return response.json()


@router.get("/search/artists")
async def search_artits(
    query: str, limit: Annotated[int, Field(default=6, lt=25, ge=1)]
):
    url = "https://musicbrainz.org/ws/2/artist/"
    params = {"query": query, "fmt": "json", "limit": limit}
    headers = {"User-Agent": "mayo-mix/0.1 (https://github.com/ammarbhat)"}
    async with httpx.AsyncClient() as client:
        response = await rate_limited_get(url, params=params, headers=headers)
        return response.json()


@router.get("/search/songs")
async def search_songs(
    query: str, limit: Annotated[int, Field(default=10, lt=25, ge=1)]
):
    mod_query = f'recording:"{query}"'
    url = "https://musicbrainz.org/ws/2/recording/"
    params = {"query": mod_query, "fmt": "json", "limit": limit}
    headers = {"User-Agent": "mayo-mix/0.1 (https://github.com/ammarbhat)"}
    async with httpx.AsyncClient() as client:
        response = await rate_limited_get(url, params=params, headers=headers)
        return response.json()


@router.get("/albums/{mbid}")
async def get_album(mbid: str):
    url = (
        f"https://musicbrainz.org/ws/2/release-group/"
        f"{mbid}?inc=genres+releases&fmt=json"
    )

    headers = {"User-Agent": "mayo-mix/0.1 (https://github.com/ammarbhat)"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await rate_limited_get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch album from MusicBrainz",
            )

        album_meta = response.json()

        # Use the release-group MBID directly
        cover_url = f"https://coverartarchive.org/" f"release-group/{mbid}/front"

        cover_response = await client.head(cover_url)

        if cover_response.status_code == 404:
            cover_url = None

    return {"meta": album_meta, "cover_url": cover_url}
