from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.react_loop import run_curation
from app.db.models import ReactStep, Roadmap
from app.db.session import get_db
from app.schemas.roadmap import (
    CurateRequest,
    CurateResponse,
    ProgressResponse,
    ProgressUpdateRequest,
    ReactStepOut,
    RoadmapListItem,
    RoadmapResponse,
)

router = APIRouter(prefix="/api")


@router.post("/curate", response_model=CurateResponse)
async def curate(body: CurateRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    roadmap = Roadmap(topic=body.topic, status="running", result_json=None, progress_json={})
    db.add(roadmap)
    await db.commit()
    await db.refresh(roadmap)

    background_tasks.add_task(run_curation, roadmap.id, body.topic)

    return CurateResponse(roadmap_id=roadmap.id)


@router.get("/roadmaps/{roadmap_id}", response_model=RoadmapResponse)
async def get_roadmap(roadmap_id: int, db: AsyncSession = Depends(get_db)):
    roadmap = await db.get(Roadmap, roadmap_id)
    if roadmap is None:
        raise HTTPException(status_code=404, detail="roadmap not found")
    return RoadmapResponse(
        id=roadmap.id,
        topic=roadmap.topic,
        status=roadmap.status,
        result=roadmap.result_json,
        progress=roadmap.progress_json or {},
        created_at=roadmap.created_at,
    )


def _resource_urls(result_json: dict | None) -> set[str]:
    if not result_json:
        return set()
    return {
        resource["url"]
        for level in result_json.get("levels", [])
        for resource in level.get("resources", [])
    }


@router.patch("/roadmaps/{roadmap_id}/progress", response_model=ProgressResponse)
async def update_progress(
    roadmap_id: int, body: ProgressUpdateRequest, db: AsyncSession = Depends(get_db)
):
    roadmap = await db.get(Roadmap, roadmap_id)
    if roadmap is None:
        raise HTTPException(status_code=404, detail="roadmap not found")
    if body.url not in _resource_urls(roadmap.result_json):
        raise HTTPException(status_code=400, detail="url is not a resource of this roadmap")

    progress = dict(roadmap.progress_json or {})
    progress[body.url] = body.completed
    roadmap.progress_json = progress
    await db.commit()

    return ProgressResponse(progress=progress)


@router.get("/roadmaps/{roadmap_id}/steps", response_model=list[ReactStepOut])
async def get_roadmap_steps(roadmap_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ReactStep).where(ReactStep.roadmap_id == roadmap_id).order_by(ReactStep.step_order)
    )
    steps = result.scalars().all()
    return [
        ReactStepOut(
            step_order=s.step_order,
            step_type=s.step_type,
            content=s.content,
            data=s.data,
            created_at=s.created_at,
        )
        for s in steps
    ]


@router.get("/roadmaps", response_model=list[RoadmapListItem])
async def list_roadmaps(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Roadmap).order_by(Roadmap.created_at.desc()))
    roadmaps = result.scalars().all()
    return [
        RoadmapListItem(id=r.id, topic=r.topic, status=r.status, created_at=r.created_at) for r in roadmaps
    ]
