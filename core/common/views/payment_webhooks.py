"""
Payment webhook views for ClustR application.
"""

import logging
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.common.models import PaymentProvider
from core.common.includes import payments

logger = logging.getLogger('clustr')


@csrf_exempt
@require_http_methods(["POST"])
def paystack_webhook(request):
    """
    Handle Paystack webhook notifications.
    """
    try:
        # Get the raw payload and signature
        payload = request.body.decode('utf-8')
        signature = request.headers.get('X-Paystack-Signature', '')
        
        if not signature:
            logger.warning("Paystack webhook received without signature")
            return HttpResponse(status=400)
        
        # Process webhook
        transaction = payments.process_webhook(
            provider=PaymentProvider.PAYSTACK,
            payload=payload,
            signature=signature
        )
        
        if transaction:
            logger.info(f"Paystack webhook processed successfully for transaction {transaction.transaction_id}")
            return HttpResponse(status=200)
        else:
            logger.warning("Paystack webhook processing failed or ignored")
            return HttpResponse(status=400)
    
    except Exception as e:
        logger.error(f"Error processing Paystack webhook: {e}")
        return HttpResponse(status=500)


@csrf_exempt
@require_http_methods(["POST"])
def flutterwave_webhook(request):
    """
    Handle Flutterwave webhook notifications.
    """
    try:
        # Get the raw payload and signature
        payload = request.body.decode('utf-8')
        signature = request.headers.get('verif-hash', '')
        
        if not signature:
            logger.warning("Flutterwave webhook received without signature")
            return HttpResponse(status=400)
        
        # Process webhook
        transaction = payments.process_webhook(
            provider=PaymentProvider.FLUTTERWAVE,
            payload=payload,
            signature=signature
        )
        
        if transaction:
            logger.info(f"Flutterwave webhook processed successfully for transaction {transaction.transaction_id}")
            return HttpResponse(status=200)
        else:
            logger.warning("Flutterwave webhook processing failed or ignored")
            return HttpResponse(status=400)
    
    except Exception as e:
        logger.error(f"Error processing Flutterwave webhook: {e}")
        return HttpResponse(status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_payment(request):
    """
    Verify a payment transaction.
    """
    try:
        transaction_id = request.data.get('transaction_id')
        
        if not transaction_id:
            return Response(
                {'error': 'Transaction ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get transaction
        from core.common.models import Transaction
        try:
            transaction = Transaction.objects.get(transaction_id=transaction_id)
        except Transaction.DoesNotExist:
            return Response(
                {'error': 'Transaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify payment
        success = payments.verify_payment(transaction)
        
        return Response({
            'transaction_id': transaction.transaction_id,
            'status': transaction.status,
            'verified': success,
            'amount': str(transaction.amount),
            'currency': transaction.currency,
        })
    
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        return Response(
            {'error': 'Payment verification failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )