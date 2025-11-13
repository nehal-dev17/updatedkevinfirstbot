from fastapi import APIRouter, HTTPException, status
from models import ProfileUpdate, ProfileResponse, ErrorResponse
from database import get_profiles_table
from datetime import datetime
from typing import Dict, Any

router = APIRouter()


@router.get(
    "/profile/{user_id}",
    response_model=ProfileResponse,
    responses={
        200: {"description": "Profile retrieved successfully"},
        500: {"model": ErrorResponse, "description": "Database error"}
    }
)
async def get_profile(user_id: int):
    """
    Get user profile by user_id.
    Returns default profile if user doesn't exist.
    """
    try:
        table = get_profiles_table()
        response = table.get_item(Key={'user_id': user_id})
        
        if 'Item' not in response:
            # Return default profile
            return ProfileResponse(
                user_id=user_id,
                age=None,
                background="Other",
                preferences={},
                history=[],
                summaries=[],
                created_at=None,
                updated_at=None
            )
        
        item = response['Item']
        return ProfileResponse(
            user_id=item.get('user_id'),
            age=item.get('age'),
            background=item.get('background', 'Other'),
            preferences=item.get('preferences', {}),
            history=item.get('history', []),
            summaries=item.get('summaries', []),
            created_at=item.get('created_at'),
            updated_at=item.get('updated_at')
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve profile: {str(e)}"
        )


@router.put(
    "/profile/{user_id}",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Profile updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        500: {"model": ErrorResponse, "description": "Database error"}
    }
)
async def update_profile(user_id: int, profile: ProfileUpdate):
    """
    Create or update user profile.
    Only updates fields that are provided in the request.
    """
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be a positive integer"
        )
    
    try:
        table = get_profiles_table()
        timestamp = datetime.utcnow().isoformat()
        
        # Check if profile exists
        existing = table.get_item(Key={'user_id': user_id})
        is_new = 'Item' not in existing
        
        # Build item to store
        item = {
            'user_id': user_id,
            'updated_at': timestamp
        }
        
        if is_new:
            item['created_at'] = timestamp
            item['history'] = []
            item['summaries'] = []
        
        # Only update provided fields
        if profile.age is not None:
            item['age'] = profile.age
        if profile.background is not None:
            item['background'] = profile.background
        if profile.preferences is not None:
            item['preferences'] = profile.preferences
        
        # Preserve existing fields if not updating
        if not is_new:
            existing_item = existing['Item']
            if profile.age is None and 'age' in existing_item:
                item['age'] = existing_item['age']
            if profile.background is None and 'background' in existing_item:
                item['background'] = existing_item['background']
            if profile.preferences is None and 'preferences' in existing_item:
                item['preferences'] = existing_item['preferences']
            if 'history' in existing_item:
                item['history'] = existing_item['history']
            if 'summaries' in existing_item:
                item['summaries'] = existing_item['summaries']
            if 'created_at' in existing_item:
                item['created_at'] = existing_item['created_at']
        
        table.put_item(Item=item)
        
        return {
            "status": "success",
            "message": "Profile updated successfully" if not is_new else "Profile created successfully",
            "user_id": user_id,
            "updated_at": timestamp
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.delete(
    "/profile/{user_id}",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Profile deleted successfully"},
        404: {"model": ErrorResponse, "description": "Profile not found"},
        500: {"model": ErrorResponse, "description": "Database error"}
    }
)
async def delete_profile(user_id: int):
    """
    Delete user profile.
    Note: This does not delete conversation history.
    """
    try:
        table = get_profiles_table()
        
        # Check if profile exists
        response = table.get_item(Key={'user_id': user_id})
        if 'Item' not in response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile not found for user_id: {user_id}"
            )
        
        # Delete profile
        table.delete_item(Key={'user_id': user_id})
        
        return {
            "status": "success",
            "message": "Profile deleted successfully",
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete profile: {str(e)}"
        )