from fastapi import APIRouter, HTTPException, status, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from models import ChatRequest, ChatResponse, HistoryResponse, ConversationItem, ErrorResponse, DeleteHistoryResponse, ConversationSummary
from database import get_conversations_table, get_profiles_table
from services.ai_service import generate_response, extract_keywords, validate_message, generate_conversation_summary
from datetime import datetime
import uuid
import boto3.dynamodb.conditions as conditions
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
@router.post(
    "/chat/{user_id}",
    response_model=ChatResponse,
    responses={
        200: {"description": "Chat response generated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "AI generation or database error"}
    }
)
@limiter.limit("50/minute")
async def chat(request: Request, user_id: int, chat_request: ChatRequest):
    """
    Main chat endpoint.
    Generates AI response based on user message, profile, and conversation history.
    Stores both user message and AI response in database.
    Rate limit: 20 requests per minute (AI generation is expensive)
    """
    # Validate user_id
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id must be a positive integer"
        )
    # Validate message
    if not validate_message(chat_request.message):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message: must be between 1 and 5000 characters"
        )
    try:
        user_message = chat_request.message
        # Get user profile
        profile_table = get_profiles_table()
        profile_response = profile_table.get_item(Key={'user_id': user_id})
        if 'Item' in profile_response:
            profile = profile_response['Item']
        else:
            # Default profile
            profile = {
                'user_id': user_id,
                'age': None,
                'background': 'Other',
                'preferences': {},
                'history': [],
                'summaries': []
            }
        # Get conversation history (last 20 messages for context)
        conv_table = get_conversations_table()
        history_response = conv_table.query(
            KeyConditionExpression=conditions.Key('user_id').eq(user_id),
            ScanIndexForward=False,
            Limit=20
        )
        conversation_items = history_response.get('Items', [])
        # Sort chronologically for context
        conversation_items = sorted(conversation_items, key=lambda x: x['timestamp'])
        # Generate AI response
        try:
            assistant_reply = await generate_response(
                user_message,
                profile,
                conversation_items
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI generation failed: {str(e)}"
            )
        # Store messages in database
        timestamp = datetime.utcnow().isoformat()
        # Extract keywords from user message
        keywords = extract_keywords(user_message)
        # Store user message
        user_item = {
            'user_id': user_id,
            'timestamp': f"{timestamp}#user#{uuid.uuid4()}",
            'role': 'user',
            'content': user_message,
            'keywords': keywords
        }
        conv_table.put_item(Item=user_item)
        # Store assistant response
        assistant_timestamp = datetime.utcnow().isoformat()
        assistant_item = {
            'user_id': user_id,
            'timestamp': f"{assistant_timestamp}#assistant#{uuid.uuid4()}",
            'role': 'assistant',
            'content': assistant_reply
        }
        conv_table.put_item(Item=assistant_item)
        # Update profile history with keywords (if any)
        if keywords:
            try:
                profile_table.update_item(
                    Key={'user_id': user_id},
                    UpdateExpression="SET #h = list_append(if_not_exists(#h, :empty_list), :vals), updated_at = :updated",
                    ExpressionAttributeNames={'#h': 'history'},
                    ExpressionAttributeValues={
                        ':vals': [{
                            'timestamp': timestamp,
                            'keywords': keywords,
                            'snippet': user_message[:100]
                        }],
                        ':empty_list': [],
                        ':updated': assistant_timestamp
                    }
                )
            except Exception:
                # Non-critical, continue even if history update fails
                pass
        return ChatResponse(
            reply=assistant_reply,
            timestamp=assistant_timestamp
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}"
        )
@router.get(
    "/history/{user_id}",
    response_model=HistoryResponse,
    responses={
        200: {"description": "History retrieved successfully"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Database error"}
    }
)
@limiter.limit("50/minute")
async def get_history(
    request: Request,
    user_id: int,
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of messages to return")
):
    """
    Get conversation history for a user.
    Returns messages in reverse chronological order (most recent first).
    Rate limit: 30 requests per minute
    """
    try:
        conv_table = get_conversations_table()
        response = conv_table.query(
            KeyConditionExpression=conditions.Key('user_id').eq(user_id),
            ScanIndexForward=False,  # Most recent first
            Limit=limit
        )
        items = response.get('Items', [])
        # Convert to ConversationItem models
        conversation_items = [
            ConversationItem(
                user_id=item['user_id'],
                timestamp=item['timestamp'],
                role=item['role'],
                content=item['content'],
                keywords=item.get('keywords', [])
            )
            for item in items
        ]
        return HistoryResponse(
            user_id=user_id,
            items=conversation_items,
            total_count=len(conversation_items)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve history: {str(e)}"
        )
@router.delete(
    "/history/{user_id}",
    response_model=DeleteHistoryResponse,
    responses={
        200: {"description": "History cleared and summary saved successfully"},
        404: {"model": ErrorResponse, "description": "No conversation history found"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Database error"}
    }
)
@limiter.limit("50/minute")
async def clear_history(request: Request, user_id: int):
    """
    Clear all conversation history for a user.
    Creates and stores a summary before deletion.
    The bot can use these summaries for future context.
    Rate limit: 5 requests per minute (expensive AI operation)
    """
    try:
        conv_table = get_conversations_table()
        profile_table = get_profiles_table()
        # Get all items for user
        response = conv_table.query(
            KeyConditionExpression=conditions.Key('user_id').eq(user_id)
        )
        items = response.get('Items', [])
        if not items:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No conversation history found for user_id: {user_id}"
            )
        # Sort items chronologically for summary
        sorted_items = sorted(items, key=lambda x: x['timestamp'])
        # Generate conversation summary using AI
        try:
            summary_data = await generate_conversation_summary(sorted_items)
        except Exception as e:
            # If summary generation fails, create a basic one
            all_keywords = []
            for item in sorted_items:
                all_keywords.extend(extract_keywords(item.get('content', '')))
            summary_data = {
                "summary": "Previous wellness conversation",
                "key_topics": list(set(all_keywords))[:5],
                "sentiment": "neutral",
                "insights": f"Conversation with {len(sorted_items)} messages"
            }
        # Create summary object
        summary_timestamp = datetime.utcnow().isoformat()
        conversation_summary = {
            "summary": summary_data.get("summary", "Previous conversation"),
            "key_topics": summary_data.get("key_topics", []),
            "sentiment": summary_data.get("sentiment", "neutral"),
            "insights": summary_data.get("insights", ""),
            "message_count": len(items),
            "created_at": summary_timestamp,
            "date_range": {
                "start": sorted_items[0]['timestamp'] if sorted_items else None,
                "end": sorted_items[-1]['timestamp'] if sorted_items else None
            }
        }
        # Store summary in user profile
        try:
            profile_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression="SET summaries = list_append(if_not_exists(summaries, :empty_list), :vals), updated_at = :updated",
                ExpressionAttributeValues={
                    ':vals': [conversation_summary],
                    ':empty_list': [],
                    ':updated': summary_timestamp
                }
            )
        except Exception as e:
            print(f"Warning: Failed to save summary: {str(e)}")
            # Continue with deletion even if summary storage fails
        # Delete all conversation items
        deleted_count = 0
        for item in items:
            conv_table.delete_item(
                Key={
                    'user_id': item['user_id'],
                    'timestamp': item['timestamp']
                }
            )
            deleted_count += 1
        return DeleteHistoryResponse(
            status="success",
            message=f"Cleared {deleted_count} messages and saved conversation summary",
            user_id=user_id,
            deleted_count=deleted_count,
            summary=ConversationSummary(
                summary=conversation_summary['summary'],
                key_topics=conversation_summary['key_topics'],
                sentiment=conversation_summary['sentiment'],
                message_count=conversation_summary['message_count'],
                created_at=conversation_summary['created_at']
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear history: {str(e)}"
        )