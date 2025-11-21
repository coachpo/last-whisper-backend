"""Translation endpoints (item-bound)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_translation_manager
from app.models.schemas import (
    ItemTranslationCreateRequest,
    TranslationResponse,
    TranslationRefreshResponse,
)

router = APIRouter(prefix="/v1", tags=["translations"])


@router.post(
    "/items/{item_id}/translations",
    response_model=TranslationResponse,
    summary="Translate an item to a target language (cached)",
)
async def translate_item(
    item_id: int,
    payload: ItemTranslationCreateRequest,
    translation_manager=Depends(get_translation_manager),
):
    result = translation_manager.translate_item(
        item_id, payload.target_lang, payload.force_refresh
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid translation request (item missing, unsupported language, or source-target identical)",
        )
    return result


@router.get(
    "/items/{item_id}/translations",
    response_model=TranslationResponse,
    summary="Fetch cached translation for an item",
)
async def get_item_translation(
    item_id: int,
    target_lang: str = Query(..., min_length=2, max_length=10),
    translation_manager=Depends(get_translation_manager),
):
    result = translation_manager.get_cached_translation(item_id, target_lang)
    if not result:
        raise HTTPException(status_code=404, detail="Cached translation not found")
    return result


@router.post(
    "/translations/{translation_id}/refresh",
    response_model=TranslationRefreshResponse,
    summary="Force refresh a translation from provider",
)
async def refresh_translation(
    translation_id: int,
    translation_manager=Depends(get_translation_manager),
):
    result = translation_manager.refresh_translation(translation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Translation not found")
    return result
