/// API configuration constants.
class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);

  // Endpoints
  static const String login = '/auth/login';
  static const String register = '/auth/register';
  static const String oauth = '/auth/oauth';
  static const String refresh = '/auth/refresh';
  static const String me = '/auth/me';

  static const String chat = '/chat/message';
  static const String conversations = '/chat/conversations';

  static const String calendars = '/calendar/calendars';
  static const String events = '/calendar/events';
  static const String checkConflicts = '/calendar/events/check-conflicts';

  static const String todos = '/todos';
  static const String todoCategories = '/todos/categories';

  static const String reminders = '/reminders';
  static const String alarms = '/alarms';
  static const String dashboard = '/dashboard';
}
