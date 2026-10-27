from django.db import transaction
from django.db.models import Count
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.exceptions import PermissionDenied, NotFound
from drf_spectacular.utils import extend_schema

from .models import Conversation, Message
from .providers.factory import get_ai_provider
from .serializers import (
    AIGuidanceRequestSerializer,
    AIGuidanceResponseSerializer,
    AISummarizeRecordRequestSerializer,
    AISummarizeResponseSerializer,
    ConversationListSerializer,
    ConversationDetailSerializer,
    ConversationCreateSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)
from apps.medical_records.models import MedicalRecord
from apps.audit.services import log_audit_event


class AIGuidanceView(APIView):
    """
    AI Healthcare Assistant Endpoint.
    Provides informational health education and symptom guidance with strict safety boundaries
    and mandatory clinical disclaimers.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"

    @extend_schema(
        tags=["AI Assistant"],
        summary="Request Health Guidance or Symptom Education",
        request=AIGuidanceRequestSerializer,
        responses={200: AIGuidanceResponseSerializer},
    )
    def post(self, request):
        serializer = AIGuidanceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data["query"]
        context = serializer.validated_data.get("context", {})

        provider = get_ai_provider()
        response_data = provider.generate_guidance(query=query, context=context)

        log_audit_event(
            event_type="AI_QUERY",
            actor=request.user,
            resource_type="AI_Guidance",
            action="GENERATE_GUIDANCE",
            details={"query_length": len(query), "provider": response_data.get("provider")},
            is_success=True,
            request=request,
        )

        return Response(
            {
                "status": "success",
                "data": response_data,
            },
            status=status.HTTP_200_OK,
        )


class AISummarizeRecordView(APIView):
    """
    AI-powered patient record summarization.
    Restricted strictly to the record owner (patient), authoring healthcare professional, or administrator.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"

    @extend_schema(
        tags=["AI Assistant"],
        summary="Summarize Medical Record into Patient-Friendly Terms",
        request=AISummarizeRecordRequestSerializer,
        responses={200: AISummarizeResponseSerializer},
    )
    def post(self, request):
        serializer = AISummarizeRecordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record_id = serializer.validated_data["record_id"]

        try:
            record = MedicalRecord.objects.select_related("patient", "patient__user", "doctor").get(pk=record_id)
        except MedicalRecord.DoesNotExist:
            raise NotFound("Medical record not found.")

        user = request.user
        is_owner = hasattr(user, "patient_profile") and record.patient_id == user.patient_profile.id
        is_doctor = hasattr(user, "doctor_profile") and record.doctor_id == user.doctor_profile.id
        is_admin = user.role == "ADMIN" or user.is_superuser

        if not (is_owner or is_doctor or is_admin):
            raise PermissionDenied("You do not have authorization to summarize this medical record.")

        provider = get_ai_provider()
        summary_data = provider.summarize_medical_record(
            title=record.title,
            description=record.description,
            clinical_data=record.clinical_data,
        )

        log_audit_event(
            event_type="AI_QUERY",
            actor=request.user,
            resource_type="MedicalRecord",
            resource_id=str(record.id),
            action="SUMMARIZE_RECORD",
            details={"record_id": record.id},
            is_success=True,
            request=request,
        )

        return Response(
            {
                "status": "success",
                "data": summary_data,
            },
            status=status.HTTP_200_OK,
        )


class ConversationListCreateView(APIView):
    """
    List user's AI conversations or initiate a new multi-turn consultation.
    Strictly isolated: users only view and create their own conversations.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"

    @extend_schema(
        tags=["AI Assistant"],
        summary="List User Conversations",
        responses={200: ConversationListSerializer(many=True)},
    )
    def get(self, request):
        conversations = (
            Conversation.objects.filter(owner=request.user)
            .annotate(message_count=Count("messages"))
            .prefetch_related("messages")
        )
        serializer = ConversationListSerializer(conversations, many=True)
        return Response(
            {
                "status": "success",
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["AI Assistant"],
        summary="Start New AI Conversation",
        request=ConversationCreateSerializer,
        responses={201: ConversationDetailSerializer},
    )
    def post(self, request):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data["query"]
        title = serializer.validated_data.get("title", "")
        if not title or title == "General Health Inquiry":
            title = query[:45].strip() + ("..." if len(query) > 45 else "")

        with transaction.atomic():
            conversation = Conversation.objects.create(
                owner=request.user,
                title=title,
            )
            # Create user message
            user_msg = Message.objects.create(
                conversation=conversation,
                role=Message.Role.USER,
                content=query,
            )
            # Generate AI guidance
            provider = get_ai_provider()
            response_data = provider.generate_guidance(query=query, context={})

            # Create assistant message
            assistant_msg = Message.objects.create(
                conversation=conversation,
                role=Message.Role.ASSISTANT,
                content=response_data.get("guidance", ""),
                metadata=response_data,
            )

        log_audit_event(
            event_type="AI_QUERY",
            actor=request.user,
            resource_type="AI_Conversation",
            resource_id=str(conversation.id),
            action="CREATE_CONVERSATION",
            details={"query_length": len(query), "conversation_id": conversation.id},
            is_success=True,
            request=request,
        )

        return Response(
            {
                "status": "success",
                "conversation": ConversationDetailSerializer(conversation).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ConversationDetailView(APIView):
    """
    Retrieve or delete an individual AI conversation thread.
    Enforces object-level ownership: only the conversation owner can access or delete it.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"

    def get_object(self, pk, user):
        try:
            return Conversation.objects.prefetch_related("messages").get(pk=pk, owner=user)
        except Conversation.DoesNotExist:
            raise NotFound("Conversation not found.")

    @extend_schema(
        tags=["AI Assistant"],
        summary="Get Conversation Messages",
        responses={200: ConversationDetailSerializer},
    )
    def get(self, request, pk):
        conversation = self.get_object(pk, request.user)
        return Response(
            {
                "status": "success",
                "conversation": ConversationDetailSerializer(conversation).data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["AI Assistant"],
        summary="Delete Conversation",
    )
    def delete(self, request, pk):
        conversation = self.get_object(pk, request.user)
        conversation_id = conversation.id
        conversation.delete()

        log_audit_event(
            event_type="AI_QUERY",
            actor=request.user,
            resource_type="AI_Conversation",
            resource_id=str(conversation_id),
            action="DELETE_CONVERSATION",
            details={"conversation_id": conversation_id},
            is_success=True,
            request=request,
        )

        return Response(
            {
                "status": "success",
                "message": "Conversation deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )


class ConversationMessageCreateView(APIView):
    """
    Post a follow-up query to an existing AI conversation.
    Appends the user question and the AI assistant's response.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"

    @extend_schema(
        tags=["AI Assistant"],
        summary="Send Follow-up Message in Conversation",
        request=MessageCreateSerializer,
        responses={201: MessageSerializer},
    )
    def post(self, request, pk):
        try:
            conversation = Conversation.objects.get(pk=pk, owner=request.user)
        except Conversation.DoesNotExist:
            raise NotFound("Conversation not found.")

        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data["query"]

        # Contextual history from the last 4 messages in this thread
        recent_messages = list(conversation.messages.order_by("-created_at")[:4])
        recent_messages.reverse()
        context = {
            "history": [{"role": m.role, "content": m.content[:200]} for m in recent_messages]
        }

        with transaction.atomic():
            user_msg = Message.objects.create(
                conversation=conversation,
                role=Message.Role.USER,
                content=query,
            )
            provider = get_ai_provider()
            response_data = provider.generate_guidance(query=query, context=context)

            assistant_msg = Message.objects.create(
                conversation=conversation,
                role=Message.Role.ASSISTANT,
                content=response_data.get("guidance", ""),
                metadata=response_data,
            )
            conversation.save(update_fields=["updated_at"])

        log_audit_event(
            event_type="AI_QUERY",
            actor=request.user,
            resource_type="AI_Conversation",
            resource_id=str(conversation.id),
            action="FOLLOW_UP_MESSAGE",
            details={"query_length": len(query), "conversation_id": conversation.id},
            is_success=True,
            request=request,
        )

        return Response(
            {
                "status": "success",
                "user_message": MessageSerializer(user_msg).data,
                "assistant_message": MessageSerializer(assistant_msg).data,
            },
            status=status.HTTP_201_CREATED,
        )
