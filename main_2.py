# Add imports at top
from utils.webhook_security import webhook_security
from utils.rate_limiter import rate_limiter

# Update SMS webhook with security
@app.post("/webhook/sms")
async def webhook_sms(request: Request):
    """
    Twilio SMS webhook endpoint with security
    """
    try:
        # Get client identifier for rate limiting
        form_data = await request.form()
        phone_number = form_data.get('From', '')
        
        # Rate limiting (max 10 SMS per minute per phone)
        allowed, retry_after = rate_limiter.check_rate_limit(
            identifier=f"sms_{phone_number}",
            max_requests=10,
            window_seconds=60
        )
        
        if not allowed:
            print(f"⚠️ Rate limit exceeded for {phone_number}")
            return Response(
                content=f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>Too many requests. Please wait {retry_after} seconds.</Message></Response>',
                media_type="application/xml",
                status_code=429
            )
        
        # Verify Twilio signature
        await webhook_security.verify_twilio_signature(request)
        
        # Extract webhook data
        webhook_data = {
            'From': form_data.get('From'),
            'To': form_data.get('To'),
            'Body': form_data.get('Body'),
            'MessageSid': form_data.get('MessageSid')
        }
        
        print(f"📱 SMS Webhook received (verified): {webhook_data}")
        
        # Process SMS
        result = await sms_handler.handle_incoming_sms(webhook_data)
        
        # Return TwiML response
        from fastapi.responses import Response
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml"
        )
        
    except HTTPException as e:
        # Security error - reject
        print(f"❌ Security error: {e.detail}")
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
            status_code=e.status_code
        )
    except Exception as e:
        print(f"❌ SMS webhook error: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
            status_code=200
        )


# Update WhatsApp webhook with security
@app.post("/webhook/whatsapp")
async def webhook_whatsapp(request: Request):
    """
    Twilio WhatsApp webhook endpoint with security
    """
    try:
        # Get client identifier for rate limiting
        form_data = await request.form()
        phone_number = form_data.get('From', '').replace('whatsapp:', '')
        
        # Rate limiting (max 10 messages per minute per phone)
        allowed, retry_after = rate_limiter.check_rate_limit(
            identifier=f"whatsapp_{phone_number}",
            max_requests=10,
            window_seconds=60
        )
        
        if not allowed:
            print(f"⚠️ Rate limit exceeded for WhatsApp {phone_number}")
            return Response(
                content=f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>Too many requests. Please wait {retry_after} seconds.</Message></Response>',
                media_type="application/xml",
                status_code=429
            )
        
        # Verify Twilio signature
        await webhook_security.verify_twilio_signature(request)
        
        # Extract webhook data
        webhook_data = {
            'From': form_data.get('From'),
            'To': form_data.get('To'),
            'Body': form_data.get('Body'),
            'MessageSid': form_data.get('MessageSid'),
            'MediaUrl0': form_data.get('MediaUrl0'),
            'NumMedia': form_data.get('NumMedia', '0')
        }
        
        print(f"💬 WhatsApp Webhook received (verified): {webhook_data}")
        
        # Process WhatsApp
        result = await whatsapp_handler.handle_incoming_whatsapp(webhook_data)
        
        # Return TwiML response
        from fastapi.responses import Response
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml"
        )
        
    except HTTPException as e:
        # Security error - reject
        print(f"❌ Security error: {e.detail}")
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
            status_code=e.status_code
        )
    except Exception as e:
        print(f"❌ WhatsApp webhook error: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
            status_code=200
        )
    


    # Add import
from utils.metrics import metrics
from fastapi.responses import Response

# Add metrics endpoint
@app.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus metrics endpoint
    """
    return Response(
        content=metrics.get_metrics(),
        media_type=metrics.get_content_type()
    )

# Update existing endpoints to record metrics
# Example for SMS webhook:
@app.post("/webhook/sms")
async def webhook_sms(request: Request):
    start_time = time.time()
    
    try:
        # ... existing code ...
        
        # Record success
        metrics.record_message('sms', 'success')
        
        duration = time.time() - start_time
        metrics.record_response_time('sms', 'webhook', duration)
        
        return Response(...)
        
    except Exception as e:
        # Record error
        metrics.record_error(type(e).__name__, 'sms')
        metrics.record_message('sms', 'error')
        raise