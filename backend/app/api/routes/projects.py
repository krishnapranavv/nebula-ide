from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import (
    CreateProjectRequest, UpdateProjectRequest, ProjectResponse,
    CreateFileRequest, UpdateFileRequest, FileResponse, FileContentResponse,
    MessageResponse,
)
from app.core.security import get_current_user
from app.core.database import (
    db_create_project, db_list_projects, db_get_project, db_update_project, db_delete_project,
    db_create_file, db_list_files, db_get_file, db_update_file, db_delete_file,
)
from app.services.storage.s3 import upload_text, download_text, delete_object, delete_prefix
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def _assert_owns_project(project: dict | None, user_id: str):
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")


def _assert_owns_file(file: dict | None, project: dict, user_id: str):
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    if file["project_id"] != project["project_id"]:
        raise HTTPException(status_code=403, detail="File does not belong to this project")


# ── Projects ──────────────────────────────────────────────────────────────────

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(body: CreateProjectRequest, user: dict = Depends(get_current_user)):
    project = await db_create_project(user["user_id"], body.name, body.language, body.description)
    logger.info(f"Project created: {project['project_id']} by {user['user_id']}")
    return project


@router.get("")
async def list_projects(user: dict = Depends(get_current_user)):
    projects = await db_list_projects(user["user_id"])
    return {"projects": projects}


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    project = await db_get_project(project_id)
    _assert_owns_project(project, user["user_id"])
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, body: UpdateProjectRequest, user: dict = Depends(get_current_user)):
    project = await db_get_project(project_id)
    _assert_owns_project(project, user["user_id"])
    updates = body.model_dump(exclude_none=True)
    updated = await db_update_project(project_id, **updates)
    return updated


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    project = await db_get_project(project_id)
    _assert_owns_project(project, user["user_id"])
    # Delete all S3 objects for this project
    await delete_prefix(project["s3_prefix"])
    await db_delete_project(project_id)
    return {"message": f"Project {project_id} deleted"}


# ── Files ─────────────────────────────────────────────────────────────────────

@router.post("/{project_id}/files", response_model=FileResponse, status_code=201)
async def create_file(project_id: str, body: CreateFileRequest, user: dict = Depends(get_current_user)):
    project = await db_get_project(project_id)
    _assert_owns_project(project, user["user_id"])

    s3_key = f"{project['s3_prefix']}{body.filename}"
    size = await upload_text(s3_key, body.content)
    record = await db_create_file(project_id, body.filename, s3_key, size)
    return record


@router.get("/{project_id}/files")
async def list_files(project_id: str, user: dict = Depends(get_current_user)):
    project = await db_get_project(project_id)
    _assert_owns_project(project, user["user_id"])
    files = await db_list_files(project_id)
    return {"files": files}


@router.get("/{project_id}/files/{file_id}", response_model=FileContentResponse)
async def get_file_content(project_id: str, file_id: str, user: dict = Depends(get_current_user)):
    project = await db_get_project(project_id)
    _assert_owns_project(project, user["user_id"])
    file = await db_get_file(file_id)
    _assert_owns_file(file, project, user["user_id"])
    content = await download_text(file["s3_key"])
    return {"file_id": file_id, "filename": file["filename"], "content": content, "updated_at": file["updated_at"]}


@router.put("/{project_id}/files/{file_id}", response_model=MessageResponse)
async def update_file_content(project_id: str, file_id: str, body: UpdateFileRequest, user: dict = Depends(get_current_user)):
    project = await db_get_project(project_id)
    _assert_owns_project(project, user["user_id"])
    file = await db_get_file(file_id)
    _assert_owns_file(file, project, user["user_id"])
    size = await upload_text(file["s3_key"], body.content)
    await db_update_file(file_id, file["s3_key"], size)
    return {"message": "File saved"}


@router.delete("/{project_id}/files/{file_id}", response_model=MessageResponse)
async def delete_file(project_id: str, file_id: str, user: dict = Depends(get_current_user)):
    project = await db_get_project(project_id)
    _assert_owns_project(project, user["user_id"])
    file = await db_get_file(file_id)
    _assert_owns_file(file, project, user["user_id"])
    await delete_object(file["s3_key"])
    await db_delete_file(file_id)
    return {"message": "File deleted"}
