import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../screens/auth/landing_screen.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/register_screen.dart';
import '../screens/dashboard/dashboard_screen.dart';
import '../screens/chat/chat_screen.dart';
import '../screens/calendar/calendar_screen.dart';
import '../screens/todos/todo_screen.dart';
import '../screens/reminders/reminders_screen.dart';
import '../screens/alarms/alarms_screen.dart';
import '../screens/settings/settings_screen.dart';
import '../providers/auth_provider.dart';
import '../widgets/main_scaffold.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authStateProvider);

  return GoRouter(
    initialLocation: '/',
    redirect: (context, state) {
      final isLoggedIn = authState.valueOrNull != null;
      final isPublicRoute = state.matchedLocation == '/' ||
          state.matchedLocation.startsWith('/auth');

      // Not logged in and trying to access protected routes
      if (!isLoggedIn && !isPublicRoute) {
        return '/auth/login';
      }
      // Logged in and on landing/auth pages -> go to dashboard
      if (isLoggedIn && (state.matchedLocation == '/' || state.matchedLocation.startsWith('/auth'))) {
        return '/dashboard';
      }
      return null;
    },
    routes: [
      // Public landing page
      GoRoute(
        path: '/',
        builder: (context, state) => const LandingScreen(),
      ),

      // Auth routes
      GoRoute(
        path: '/auth/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/auth/register',
        builder: (context, state) => const RegisterScreen(),
      ),

      // Main app with bottom navigation (protected)
      ShellRoute(
        builder: (context, state, child) => MainScaffold(child: child),
        routes: [
          GoRoute(
            path: '/dashboard',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: DashboardScreen(),
            ),
          ),
          GoRoute(
            path: '/chat',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: ChatScreen(),
            ),
          ),
          GoRoute(
            path: '/calendar',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: CalendarScreen(),
            ),
          ),
          GoRoute(
            path: '/todos',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: TodoScreen(),
            ),
          ),
          GoRoute(
            path: '/reminders',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: RemindersScreen(),
            ),
          ),
          GoRoute(
            path: '/alarms',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: AlarmsScreen(),
            ),
          ),
          GoRoute(
            path: '/settings',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: SettingsScreen(),
            ),
          ),
        ],
      ),
    ],
  );
});
