/// Chat and conversation models.

class ConversationModel {
  final String id;
  final String title;
  final String? summary;
  final DateTime createdAt;
  final DateTime updatedAt;
  final int messageCount;

  const ConversationModel({
    required this.id,
    required this.title,
    this.summary,
    required this.createdAt,
    required this.updatedAt,
    this.messageCount = 0,
  });

  factory ConversationModel.fromJson(Map<String, dynamic> json) {
    return ConversationModel(
      id: json['id'],
      title: json['title'],
      summary: json['summary'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
      messageCount: json['message_count'] ?? 0,
    );
  }
}

class MessageModel {
  final String id;
  final String conversationId;
  final String role;
  final String content;
  final String? intentDetected;
  final List<dynamic> actionsTaken;
  final DateTime createdAt;

  const MessageModel({
    required this.id,
    required this.conversationId,
    required this.role,
    required this.content,
    this.intentDetected,
    this.actionsTaken = const [],
    required this.createdAt,
  });

  factory MessageModel.fromJson(Map<String, dynamic> json) {
    return MessageModel(
      id: json['id'],
      conversationId: json['conversation_id'],
      role: json['role'],
      content: json['content'],
      intentDetected: json['intent_detected'],
      actionsTaken: json['actions_taken'] ?? [],
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  bool get isUser => role == 'user';
  bool get isAssistant => role == 'assistant';
}

class ChatResponseModel {
  final MessageModel message;
  final List<AIActionModel> actions;
  final List<String> followUpQuestions;

  const ChatResponseModel({
    required this.message,
    this.actions = const [],
    this.followUpQuestions = const [],
  });

  factory ChatResponseModel.fromJson(Map<String, dynamic> json) {
    return ChatResponseModel(
      message: MessageModel.fromJson(json['message']),
      actions: (json['actions'] as List?)
          ?.map((a) => AIActionModel.fromJson(a))
          .toList() ?? [],
      followUpQuestions: List<String>.from(json['follow_up_questions'] ?? []),
    );
  }
}

class AIActionModel {
  final String actionType;
  final Map<String, dynamic> parameters;
  final bool confirmationNeeded;
  final String message;

  const AIActionModel({
    required this.actionType,
    required this.parameters,
    this.confirmationNeeded = false,
    required this.message,
  });

  factory AIActionModel.fromJson(Map<String, dynamic> json) {
    return AIActionModel(
      actionType: json['action_type'],
      parameters: json['parameters'] ?? {},
      confirmationNeeded: json['confirmation_needed'] ?? false,
      message: json['message'] ?? '',
    );
  }
}
