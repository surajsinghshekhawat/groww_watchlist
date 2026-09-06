from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.api.dependencies import CurrentUser, DbSession
from app.core.rate_limit import enforce_rate_limit
from app.schemas.watchlist import (
    AddInstrumentRequest,
    InstrumentResponse,
    IntentCreateRequest,
    IntentWatchlistRequest,
    UpdateItemNoteRequest,
    WatchlistCreate,
    WatchlistPriceRow,
    WatchlistResponse,
    WatchlistUpdate,
)
from app.services.intent_watchlist import (
    create_watchlist_from_selection,
    preview_watchlist_from_intent,
)
from app.services.watchlist_service import WatchlistService

router = APIRouter(tags=["watchlists"])


@router.get("/watchlists", response_model=list[WatchlistResponse])
async def list_watchlists(user: CurrentUser, session: DbSession) -> list[WatchlistResponse]:
    return await WatchlistService(session).list_mine(user.user_id)


@router.post("/watchlists", response_model=WatchlistResponse, status_code=201)
async def create_watchlist(
    request: Request,
    payload: WatchlistCreate,
    user: CurrentUser,
    session: DbSession,
) -> WatchlistResponse:
    await enforce_rate_limit(request, scope="watchlist_create", limit=30, window_seconds=60)
    return await WatchlistService(session).create(user.user_id, payload)


@router.post("/watchlists/from-intent/preview")
async def preview_watchlist_from_nlp(
    request: Request,
    payload: IntentWatchlistRequest,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Describe → preview matches. Does not create a watchlist yet."""
    await enforce_rate_limit(request, scope="watchlist_intent_preview", limit=20, window_seconds=60)
    _ = user
    return await preview_watchlist_from_intent(session, payload.prompt)


@router.post("/watchlists/from-intent/confirm", status_code=201)
async def confirm_watchlist_from_nlp(
    request: Request,
    payload: IntentCreateRequest,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Create a brand-new watchlist from the user-confirmed selection."""
    await enforce_rate_limit(request, scope="watchlist_intent_confirm", limit=10, window_seconds=60)
    return await create_watchlist_from_selection(
        session,
        user.user_id,
        name=payload.name,
        instrument_ids=payload.instrument_ids,
        note=payload.note,
        prompt=payload.prompt,
    )


@router.post("/watchlists/from-intent")
async def create_watchlist_from_nlp(
    request: Request,
    payload: IntentWatchlistRequest,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Deprecated one-shot — prefer preview then confirm."""
    await enforce_rate_limit(request, scope="watchlist_intent", limit=10, window_seconds=60)
    preview = await preview_watchlist_from_intent(session, payload.prompt)
    from uuid import UUID as _UUID

    created = await create_watchlist_from_selection(
        session,
        user.user_id,
        name=preview["proposed_name"],
        instrument_ids=[_UUID(m["instrument_id"]) for m in preview["matches"]],
        note=preview["rationale"],
        prompt=payload.prompt,
    )
    return {
        "watchlist": created["watchlist"],
        "plan": {
            "watchlist_name": preview["proposed_name"],
            "symbols_requested": preview["symbols_requested"],
            "sectors_requested": preview["sectors_requested"],
            "themes": preview["themes"],
            "rationale": preview["rationale"],
            "matched_symbols": created["matched_symbols"],
            "model": preview["model"],
        },
    }


@router.get("/watchlists/{watchlist_id}", response_model=WatchlistResponse)
async def get_watchlist(
    watchlist_id: UUID, user: CurrentUser, session: DbSession
) -> WatchlistResponse:
    return await WatchlistService(session).get(user.user_id, watchlist_id)


@router.patch("/watchlists/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(
    watchlist_id: UUID,
    payload: WatchlistUpdate,
    user: CurrentUser,
    session: DbSession,
) -> WatchlistResponse:
    return await WatchlistService(session).update(user.user_id, watchlist_id, payload)


@router.delete("/watchlists/{watchlist_id}", status_code=204)
async def delete_watchlist(
    watchlist_id: UUID, user: CurrentUser, session: DbSession
) -> None:
    await WatchlistService(session).delete(user.user_id, watchlist_id)


@router.post(
    "/watchlists/{watchlist_id}/instruments",
    response_model=WatchlistResponse,
)
async def add_instrument(
    watchlist_id: UUID,
    payload: AddInstrumentRequest,
    user: CurrentUser,
    session: DbSession,
    request: Request,
) -> WatchlistResponse:
    await enforce_rate_limit(request, scope="watchlist_mutate", limit=60, window_seconds=60)
    return await WatchlistService(session).add_instrument(user.user_id, watchlist_id, payload)


@router.delete(
    "/watchlists/{watchlist_id}/instruments/{instrument_id}",
    response_model=WatchlistResponse,
)
async def remove_instrument(
    watchlist_id: UUID,
    instrument_id: UUID,
    user: CurrentUser,
    session: DbSession,
    version: int = Query(..., ge=1),
) -> WatchlistResponse:
    return await WatchlistService(session).remove_instrument(
        user.user_id, watchlist_id, instrument_id, version=version
    )


@router.patch(
    "/watchlists/{watchlist_id}/instruments/{instrument_id}/note",
    response_model=WatchlistResponse,
)
async def update_item_note(
    watchlist_id: UUID,
    instrument_id: UUID,
    payload: UpdateItemNoteRequest,
    user: CurrentUser,
    session: DbSession,
) -> WatchlistResponse:
    return await WatchlistService(session).update_item_note(
        user.user_id, watchlist_id, instrument_id, payload
    )


@router.get("/instruments/search", response_model=list[InstrumentResponse])
async def search_instruments(
    user: CurrentUser,
    session: DbSession,
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(20, ge=1, le=50),
) -> list[InstrumentResponse]:
    return await WatchlistService(session).search_instruments(q, limit=limit)


@router.get(
    "/watchlists/{watchlist_id}/prices",
    response_model=list[WatchlistPriceRow],
)
async def watchlist_prices(
    watchlist_id: UUID, user: CurrentUser, session: DbSession
) -> list[WatchlistPriceRow]:
    return await WatchlistService(session).price_rows(user.user_id, watchlist_id)
