from django.urls import path
from .views import (
    AIGuidanceView,
    AISummarizeRecordView,
    ConversationListCreateView,
    ConversationDetailView,
    ConversationMessageCreateView,
)

urlpatterns = [
    path("guidance/", AIGuidanceView.as_view(), name="ai-guidance"),
    path("summarize-record/", AISummarizeRecordView.as_view(), name="ai-summarize-record"),
    path("conversations/", ConversationListCreateView.as_view(), name="ai-conversation-list-create"),
    path("conversations/<int:pk>/", ConversationDetailView.as_view(), name="ai-conversation-detail"),
    path("conversations/<int:pk>/messages/", ConversationMessageCreateView.as_view(), name="ai-conversation-message-create"),
]
