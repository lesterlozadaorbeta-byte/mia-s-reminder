import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../config/api_config.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';

/// Dashboard data provider
final dashboardProvider = FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final api = ref.read(apiServiceProvider);
  final response = await api.dio.get(ApiConfig.dashboard);
  return response.data;
});

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardAsync = ref.watch(dashboardProvider);

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Good morning!'),
            Text(
              DateFormat('EEEE, MMMM d').format(DateTime.now()),
              style: TextStyle(fontSize: 13, color: Colors.grey[600]),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () {},
          ),
        ],
      ),
      body: dashboardAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (data) => _buildDashboard(context, data),
      ),
    );
  }

  Widget _buildDashboard(BuildContext context, Map<String, dynamic> data) {
    final stats = data['stats'] as Map<String, dynamic>;
    final todayEvents = data['today_events'] as List;
    final pendingTodos = data['pending_todos'] as List;
    final upcomingReminders = data['upcoming_reminders'] as List;

    return RefreshIndicator(
      onRefresh: () async {},
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Stats cards
          _buildStatsRow(stats),
          const SizedBox(height: 24),

          // Today's schedule
          _buildSectionHeader(context, 'Today\'s Schedule', Icons.calendar_today),
          const SizedBox(height: 12),
          if (todayEvents.isEmpty)
            _buildEmptyCard('No events today')
          else
            ...todayEvents.map((e) => _buildEventCard(context, e)),

          const SizedBox(height: 24),

          // Pending tasks
          _buildSectionHeader(context, 'Pending Tasks', Icons.checklist),
          const SizedBox(height: 12),
          if (pendingTodos.isEmpty)
            _buildEmptyCard('All tasks completed!')
          else
            ...pendingTodos.take(5).map((t) => _buildTodoCard(context, t)),

          const SizedBox(height: 24),

          // Upcoming reminders
          _buildSectionHeader(context, 'Upcoming Reminders', Icons.notifications_active),
          const SizedBox(height: 12),
          if (upcomingReminders.isEmpty)
            _buildEmptyCard('No upcoming reminders')
          else
            ...upcomingReminders.take(5).map((r) => _buildReminderCard(context, r)),

          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _buildStatsRow(Map<String, dynamic> stats) {
    return Row(
      children: [
        Expanded(
          child: _buildStatCard(
            'Completion',
            '${stats['completion_rate']}%',
            Icons.trending_up,
            AppTheme.successColor,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildStatCard(
            'This Week',
            '${stats['weekly_completed']}',
            Icons.check_circle_outline,
            AppTheme.primaryColor,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildStatCard(
            'Today',
            '${stats['today_event_count']}',
            Icons.event,
            AppTheme.accentColor,
          ),
        ),
      ],
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(fontSize: 12, color: Colors.grey[600]),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(BuildContext context, String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 20, color: AppTheme.primaryColor),
        const SizedBox(width: 8),
        Text(
          title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyCard(String message) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: Text(message, style: TextStyle(color: Colors.grey[500])),
        ),
      ),
    );
  }

  Widget _buildEventCard(BuildContext context, Map<String, dynamic> event) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Container(
          width: 4,
          height: 40,
          decoration: BoxDecoration(
            color: Color(int.parse((event['color'] ?? '#6366F1').replaceFirst('#', '0xFF'))),
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        title: Text(event['title'], style: const TextStyle(fontWeight: FontWeight.w500)),
        subtitle: Text(
          '${_formatTime(event['start_time'])} - ${_formatTime(event['end_time'])}',
          style: TextStyle(color: Colors.grey[600], fontSize: 13),
        ),
        trailing: event['location'] != null
            ? const Icon(Icons.location_on_outlined, size: 18)
            : null,
      ),
    );
  }

  Widget _buildTodoCard(BuildContext context, Map<String, dynamic> todo) {
    final priorityColors = {1: AppTheme.priorityUrgent, 2: AppTheme.priorityHigh, 3: AppTheme.priorityMedium, 4: AppTheme.priorityLow};
    final color = priorityColors[todo['priority']] ?? Colors.grey;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(Icons.radio_button_unchecked, color: color),
        title: Text(todo['title'], style: const TextStyle(fontWeight: FontWeight.w500)),
        subtitle: todo['due_date'] != null
            ? Text('Due: ${_formatDate(todo['due_date'])}', style: TextStyle(color: Colors.grey[600], fontSize: 13))
            : null,
        trailing: CircularProgressIndicator(
          value: (todo['progress_percent'] ?? 0) / 100,
          strokeWidth: 3,
          backgroundColor: Colors.grey[200],
          color: color,
        ),
      ),
    );
  }

  Widget _buildReminderCard(BuildContext context, Map<String, dynamic> reminder) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          reminder['is_persistent'] == true ? Icons.notifications_active : Icons.notifications_outlined,
          color: AppTheme.warningColor,
        ),
        title: Text(reminder['title'], style: const TextStyle(fontWeight: FontWeight.w500)),
        subtitle: Text(
          _formatDateTime(reminder['remind_at']),
          style: TextStyle(color: Colors.grey[600], fontSize: 13),
        ),
      ),
    );
  }

  String _formatTime(String iso) {
    final dt = DateTime.parse(iso);
    return DateFormat('HH:mm').format(dt);
  }

  String _formatDate(String iso) {
    final dt = DateTime.parse(iso);
    return DateFormat('MMM d').format(dt);
  }

  String _formatDateTime(String iso) {
    final dt = DateTime.parse(iso);
    return DateFormat('MMM d, HH:mm').format(dt);
  }
}
