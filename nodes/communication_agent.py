"""
Communication Agent - Handles Email/SMS/WhatsApp
"""

from state.workflow_state import WorkflowState, lead_reducer
from services.email_service import send_email, get_email_template
from services.sms_service import send_sms, get_sms_template
from services.whatsapp_service import send_whatsapp, get_whatsapp_template
from datetime import datetime

async def communication_agent(state: WorkflowState) -> WorkflowState:
    """
    Execute communication based on detected intent and channel
    """
    
    actions = state.get("actions_to_execute", [])
    entities = state.get("entities_extracted", {})
    lead_data = state.lead_data
    
    action_summary = []
    
    # Execute each action
    for action in actions:
        
        # Schedule Callback
        if action == "schedule_callback":
            callback_time = entities.get("callback_time")
            phone = entities.get("phone") or lead_data.get("phone")
            
            if callback_time and phone:
                # Send SMS confirmation
                message = get_sms_template(
                    "callback_confirmation",
                    callback_time=callback_time,
                    phone=phone
                )
                await send_sms(phone, message)
                action_summary.append(f"Callback scheduled for {callback_time}, SMS sent")
        
        # Send Email
        elif action == "send_email":
            email = entities.get("email") or lead_data.get("email")
            details_type = entities.get("details_type", "general")
            
            if email:
                # Get appropriate template
                if details_type == "pricing":
                    subject = "TechCorp Pricing Details"
                    body = get_email_template(
                        "pricing_details",
                        name=lead_data.get("name", "Customer"),
                        pricing_content="<p>Our pricing starts at $99/month...</p>"
                    )
                elif details_type == "product":
                    subject = "TechCorp Product Catalog"
                    body = get_email_template(
                        "product_catalog",
                        name=lead_data.get("name", "Customer")
                    )
                else:
                    subject = "Information from TechCorp"
                    body = f"<p>Dear {lead_data.get('name', 'Customer')},</p><p>Here's the information you requested.</p>"
                
                success = await send_email(email, subject, body)
                if success:
                    action_summary.append(f"Email sent to {email}")
        
        # Send SMS
        elif action == "send_sms":
            phone = entities.get("phone") or lead_data.get("phone")
            details_type = entities.get("details_type", "general")
            
            if phone:
                message = get_sms_template(
                    "pricing_sent" if details_type == "pricing" else "general_confirmation",
                    support_number="+1-800-TECHCORP"
                )
                success = await send_sms(phone, message)
                if success:
                    action_summary.append(f"SMS sent to {phone}")
        
        # Send WhatsApp
        elif action == "send_whatsapp":
            whatsapp = entities.get("whatsapp_number") or lead_data.get("phone")
            details_type = entities.get("details_type", "product")
            
            if whatsapp:
                message = get_whatsapp_template(
                    "product_catalog" if details_type == "product" else "pricing_details",
                    name=lead_data.get("name", "Customer"),
                    pricing_content="Check our website for latest pricing"
                )
                
                # Optional: attach media
                media_url = None  # Could be PDF URL
                
                success = await send_whatsapp(whatsapp, message, media_url)
                if success:
                    action_summary.append(f"WhatsApp sent to {whatsapp}")
    
    # Update state
    updates = {
        "last_contacted_at": datetime.now().isoformat(),
        "conversation_thread": state.conversation_thread + [
            f"[{datetime.now().isoformat()}] Actions executed: {', '.join(action_summary)}"
        ],
        "channel_history": state.channel_history + [entities.get("channel", "unknown")],
        "pending_action": None
    }
    
    updated_state = lead_reducer(state, updates)
    print(f"✅ Communication Agent: {', '.join(action_summary)}")
    
    return updated_state