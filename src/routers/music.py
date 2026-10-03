from fastapi import Depends, HTTPException, APIRouter
from src.models import User, CachedEntity
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
from src.config import settings
from datetime import datetime, timedelta, timezone

router = APIRouter()


musicbrainz_semaphore = asyncio.Semaphore(1)
CACHE_TTL = timedelta(days=13)


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
    headers = {"User-Agent": settings.MUSICBRAINZ_USER_AGENT}

    async with httpx.AsyncClient() as client:
        response = await rate_limited_get(url, params=params, headers=headers)
        return response.json()


@router.get("/search/artists")
async def search_artits(
    query: str, limit: Annotated[int, Field(default=6, lt=25, ge=1)]
):
    url = "https://musicbrainz.org/ws/2/artist/"
    params = {"query": query, "fmt": "json", "limit": limit}
    headers = {"User-Agent": settings.MUSICBRAINZ_USER_AGENT}
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
    headers = {"User-Agent": settings.MUSICBRAINZ_USER_AGENT}
    async with httpx.AsyncClient() as client:
        response = await rate_limited_get(url, params=params, headers=headers)
        return response.json()


@router.get("/albums/{mbid}")
async def get_album(mbid: str, db=Depends(get_db)):
    url = (
        f"https://musicbrainz.org/ws/2/release-group/"
        f"{mbid}?inc=genres+releases&fmt=json"
    )
    cached = db.query(CachedEntity).filter(CachedEntity.mbid == mbid).first()
    if cached and (datetime.now(timezone.utc) - cached.fetched_date) < CACHE_TTL:
        return cached.data

    headers = {"User-Agent": settings.MUSICBRAINZ_USER_AGENT}

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

    if cached:
        cached.data = album_meta
        cached.fetched_at = datetime.now(timezone.utc)
    else:
        db.add(
            CachedEntity(
                mbid=mbid, data=album_meta, fetched_date=datetime.now(timezone.utc)
            )
        )
    db.commit()
    return {"meta": album_meta, "cover_url": cover_url}
