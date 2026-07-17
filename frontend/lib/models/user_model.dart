/// User model.
class UserModel {
  final String id;
  final String email;
  final String fullName;
  final String? avatarUrl;
  final String authProvider;
  final String timezone;
  final String language;
  final String theme;
  final String? telegramChatId;
  final Map<String, dynamic> notificationPreferences;
  final bool isActive;
  final bool isVerified;
  final DateTime createdAt;
  final DateTime? lastLoginAt;

  const UserModel({
    required this.id,
    required this.email,
    required this.fullName,
    this.avatarUrl,
    required this.authProvider,
    this.timezone = 'UTC',
    this.language = 'en',
    this.theme = 'system',
    this.telegramChatId,
    this.notificationPreferences = const {},
    this.isActive = true,
    this.isVerified = false,
    required this.createdAt,
    this.lastLoginAt,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'],
      email: json['email'],
      fullName: json['full_name'],
      avatarUrl: json['avatar_url'],
      authProvider: json['auth_provider'] ?? 'email',
      timezone: json['timezone'] ?? 'UTC',
      language: json['language'] ?? 'en',
      theme: json['theme'] ?? 'system',
      telegramChatId: json['telegram_chat_id'],
      notificationPreferences: json['notification_preferences'] ?? {},
      isActive: json['is_active'] ?? true,
      isVerified: json['is_verified'] ?? false,
      createdAt: DateTime.parse(json['created_at']),
      lastLoginAt: json['last_login_at'] != null
          ? DateTime.parse(json['last_login_at'])
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'email': email,
    'full_name': fullName,
    'avatar_url': avatarUrl,
    'auth_provider': authProvider,
    'timezone': timezone,
    'language': language,
    'theme': theme,
    'telegram_chat_id': telegramChatId,
    'notification_preferences': notificationPreferences,
  };
}
