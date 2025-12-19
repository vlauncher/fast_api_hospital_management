from app.core.celery_app import celery_app
from app.services import ai_service
from loguru import logger
import asyncio

@celery_app.task(name="app.tasks.predict_bed_occupancy")
def predict_bed_occupancy(department_id: str, historical_data: dict):
    """
    Celery task to predict bed occupancy using AI.
    """
    logger.info(f"Starting bed occupancy prediction for dept: {department_id}")
    
    # In a real scenario, this would be an async call, but Celery tasks are sync by default.
    # We can use asyncio.run or make it an async task if using special libraries.
    # For now, we'll just demonstrate the flow.
    
    prompt = f"Based on this historical data: {historical_data}, predict the bed occupancy for the next 7 days."
    
    # Use loop for async service call
    loop = asyncio.get_event_loop()
    prediction = loop.run_until_complete(ai_service.generate_content(prompt))
    
    logger.info(f"Prediction complete for {department_id}")
    return prediction

@celery_app.task(name="app.tasks.inventory_forecast")
def inventory_forecast(item_id: str, historical_usage: dict):
    """
    Celery task to forecast inventory demand.
    """
    logger.info(f"Starting inventory forecast for item: {item_id}")
    
    prompt = f"Forecast demand for inventory item {item_id} based on: {historical_usage}"
    
    loop = asyncio.get_event_loop()
    forecast = loop.run_until_complete(ai_service.generate_content(prompt))
    
    return forecast
