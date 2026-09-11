from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.react_loop import run_curation
from app.db.models import ReactStep, Roadmap
from app.db.session import get_db
from app.schemas.roadmap import (
    CurateRequest,
    CurateResponse,
    ReactStepOut,
    RoadmapListItem,
    RoadmapResponse,
)

router = APIRouter(prefix="/api")


@router.post("/curate", response_model=CurateResponse)
async def curate(body: CurateRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    roadmap = Roadmap(topic=body.topic, status="running", result_json=None)
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
        created_at=roadmap.created_at,
    )


@router.get("/roadmaps/{roadmap_id}/steps", response_model=list[ReactStepOut])
async def get_roadmap_steps(roadmap_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ReactStep).where(ReactStep.roadmap_id == roadmap_id).order_by(ReactStep.step_order)
    )
    steps = result.scalars().all()
    return [
        ReactStepOut(
            step_order=s.step_order, step_type=s.step_type, content=s.content, created_at=s.created_at
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
