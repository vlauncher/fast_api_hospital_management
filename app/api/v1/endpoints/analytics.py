from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from app.api import deps
from app.tasks import predictive_analytics
from app.models.user import User, UserRole

router = APIRouter()

@router.post("/predict-bed-occupancy")
async def trigger_bed_prediction(
    department_id: str,
    historical_data: dict,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    task = predictive_analytics.predict_bed_occupancy.delay(department_id, historical_data)
    return {"task_id": task.id, "status": "Prediction started"}

@router.post("/inventory-forecast")
async def trigger_inventory_forecast(
    item_id: str,
    historical_usage: dict,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    task = predictive_analytics.inventory_forecast.delay(item_id, historical_usage)
    return {"task_id": task.id, "status": "Forecasting started"}
