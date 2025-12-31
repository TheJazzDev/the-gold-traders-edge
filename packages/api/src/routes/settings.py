"""
Settings API Routes

Provides endpoints for managing application settings via admin panel.
All settings are stored in PostgreSQL and can be updated without redeploying.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from enum import Enum
import sys
from pathlib import Path

# Add engine to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'engine' / 'src'))

from database.connection import get_db
from database.settings_models import Setting, SettingCategory
from database.settings_repository import SettingsRepository
from sqlalchemy.orm import Session

router = APIRouter(prefix="/v1/settings", tags=["settings"])


# ==================== PYDANTIC MODELS ====================

class SettingResponse(BaseModel):
    """Setting response model"""
    id: int
    key: str
    category: str
    value: str
    value_type: str
    typed_value: Any  # Actual typed value
    default_value: str
    description: Optional[str]
    unit: Optional[str]
    min_value: Optional[float]
    max_value: Optional[float]
    editable: bool
    requires_restart: bool
    last_modified_by: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class SettingUpdateRequest(BaseModel):
    """Request to update a setting"""
    value: Any = Field(..., description="New value for the setting")
    modified_by: str = Field(default="admin", description="User making the change")


class BulkSettingsUpdateRequest(BaseModel):
    """Request to update multiple settings at once"""
    settings: Dict[str, Any] = Field(..., description="Dictionary of key: value pairs")
    modified_by: str = Field(default="admin", description="User making the changes")


class SettingsCategoryResponse(BaseModel):
    """Settings grouped by category"""
    category: str
    settings: List[SettingResponse]


# ==================== ROUTES ====================

@router.get("/", response_model=List[SettingResponse])
async def get_all_settings(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all settings or filter by category.

    Args:
        category: Optional category filter (trading, risk_management, strategies, notifications, system)

    Returns:
        List of all settings with their current values
    """
    repo = SettingsRepository(db)

    if category:
        try:
            cat_enum = SettingCategory(category)
            settings = repo.get_by_category(cat_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    else:
        settings = repo.get_all()

    return [
        SettingResponse(
            id=s.id,
            key=s.key,
            category=s.category.value,
            value=s.value,
            value_type=s.value_type,
            typed_value=s.get_typed_value(),
            default_value=s.default_value,
            description=s.description,
            unit=s.unit,
            min_value=s.min_value,
            max_value=s.max_value,
            editable=s.editable,
            requires_restart=s.requires_restart,
            last_modified_by=s.last_modified_by,
            updated_at=s.updated_at.isoformat() if s.updated_at else None
        )
        for s in settings
    ]


@router.get("/categories", response_model=List[SettingsCategoryResponse])
async def get_settings_by_category(db: Session = Depends(get_db)):
    """
    Get all settings grouped by category.

    Returns:
        Settings organized by category for easier UI rendering
    """
    repo = SettingsRepository(db)
    result = []

    for category in SettingCategory:
        settings = repo.get_by_category(category)
        if settings:
            result.append(SettingsCategoryResponse(
                category=category.value,
                settings=[
                    SettingResponse(
                        id=s.id,
                        key=s.key,
                        category=s.category.value,
                        value=s.value,
                        value_type=s.value_type,
                        typed_value=s.get_typed_value(),
                        default_value=s.default_value,
                        description=s.description,
                        unit=s.unit,
                        min_value=s.min_value,
                        max_value=s.max_value,
                        editable=s.editable,
                        requires_restart=s.requires_restart,
                        last_modified_by=s.last_modified_by,
                        updated_at=s.updated_at.isoformat() if s.updated_at else None
                    )
                    for s in settings
                ]
            ))

    return result


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str, db: Session = Depends(get_db)):
    """
    Get a specific setting by key.

    Args:
        key: Setting key (e.g., 'max_risk_per_trade')

    Returns:
        Setting details
    """
    repo = SettingsRepository(db)
    setting = repo.get_setting(key)

    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    return SettingResponse(
        id=setting.id,
        key=setting.key,
        category=setting.category.value,
        value=setting.value,
        value_type=setting.value_type,
        typed_value=setting.get_typed_value(),
        default_value=setting.default_value,
        description=setting.description,
        unit=setting.unit,
        min_value=setting.min_value,
        max_value=setting.max_value,
        editable=setting.editable,
        requires_restart=setting.requires_restart,
        last_modified_by=setting.last_modified_by,
        updated_at=setting.updated_at.isoformat() if setting.updated_at else None
    )


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    request: SettingUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update a setting value.

    Args:
        key: Setting key
        request: Update request with new value

    Returns:
        Updated setting

    Raises:
        404: Setting not found
        400: Invalid value or setting not editable
    """
    repo = SettingsRepository(db)

    # Validate setting exists
    setting = repo.get_setting(key)
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    # Update
    success = repo.set(key, request.value, request.modified_by)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update setting '{key}'. Check if value is within valid range."
        )

    # Return updated setting
    updated_setting = repo.get_setting(key)
    return SettingResponse(
        id=updated_setting.id,
        key=updated_setting.key,
        category=updated_setting.category.value,
        value=updated_setting.value,
        value_type=updated_setting.value_type,
        typed_value=updated_setting.get_typed_value(),
        default_value=updated_setting.default_value,
        description=updated_setting.description,
        unit=updated_setting.unit,
        min_value=updated_setting.min_value,
        max_value=updated_setting.max_value,
        editable=updated_setting.editable,
        requires_restart=updated_setting.requires_restart,
        last_modified_by=updated_setting.last_modified_by,
        updated_at=updated_setting.updated_at.isoformat() if updated_setting.updated_at else None
    )


@router.put("/bulk/update")
async def bulk_update_settings(
    request: BulkSettingsUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update multiple settings at once.

    Args:
        request: Bulk update request with multiple key-value pairs

    Returns:
        Summary of updates

    Example:
        {
            "settings": {
                "max_risk_per_trade": 2.0,
                "max_positions": 10,
                "auto_trading_enabled": true
            },
            "modified_by": "admin@example.com"
        }
    """
    repo = SettingsRepository(db)
    results = {
        "updated": [],
        "failed": [],
        "requires_restart": []
    }

    for key, value in request.settings.items():
        setting = repo.get_setting(key)

        if not setting:
            results["failed"].append({"key": key, "reason": "Setting not found"})
            continue

        success = repo.set(key, value, request.modified_by)

        if success:
            results["updated"].append(key)
            if setting.requires_restart:
                results["requires_restart"].append(key)
        else:
            results["failed"].append({"key": key, "reason": "Update failed (check value range)"})

    return {
        "success": len(results["failed"]) == 0,
        "updated_count": len(results["updated"]),
        "failed_count": len(results["failed"]),
        "requires_restart": len(results["requires_restart"]) > 0,
        "details": results
    }


@router.post("/{key}/reset")
async def reset_setting_to_default(
    key: str,
    modified_by: str = "admin",
    db: Session = Depends(get_db)
):
    """
    Reset a setting to its default value.

    Args:
        key: Setting key
        modified_by: User making the change

    Returns:
        Reset setting
    """
    repo = SettingsRepository(db)
    success = repo.reset_to_default(key, modified_by)

    if not success:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    # Return updated setting
    setting = repo.get_setting(key)
    return SettingResponse(
        id=setting.id,
        key=setting.key,
        category=setting.category.value,
        value=setting.value,
        value_type=setting.value_type,
        typed_value=setting.get_typed_value(),
        default_value=setting.default_value,
        description=setting.description,
        unit=setting.unit,
        min_value=setting.min_value,
        max_value=setting.max_value,
        editable=setting.editable,
        requires_restart=setting.requires_restart,
        last_modified_by=setting.last_modified_by,
        updated_at=setting.updated_at.isoformat() if setting.updated_at else None
    )


@router.post("/reset-all")
async def reset_all_settings(
    modified_by: str = "admin",
    db: Session = Depends(get_db)
):
    """
    Reset ALL settings to their default values.

    ⚠️ USE WITH CAUTION - This will reset all configurable settings!

    Args:
        modified_by: User making the change

    Returns:
        Confirmation message
    """
    repo = SettingsRepository(db)
    repo.reset_all_to_defaults(modified_by)

    return {
        "success": True,
        "message": "All settings reset to defaults",
        "modified_by": modified_by
    }


@router.get("/service/status")
async def get_service_status(db: Session = Depends(get_db)):
    """
    Get current service status and key settings.

    Returns:
        Service configuration summary
    """
    repo = SettingsRepository(db)

    return {
        "status": repo.get("service_status", "running"),
        "service_status": repo.get("service_status", "running"),
        "auto_trading_enabled": repo.get("auto_trading_enabled", False),
        "dry_run_mode": repo.get("dry_run_mode", False),
        "max_risk_per_trade": repo.get("max_risk_per_trade", 1.0),
        "max_positions": repo.get("max_positions", 5),
        "enabled_timeframes": repo.get("enabled_timeframes", []),
        "enabled_strategies": repo.get("enabled_strategies", []),
        "data_feed_type": repo.get("data_feed_type", "metaapi"),
        "active_timeframes": repo.get("enabled_timeframes", ["5m", "15m", "30m", "1h", "4h", "1d"]),
    }
