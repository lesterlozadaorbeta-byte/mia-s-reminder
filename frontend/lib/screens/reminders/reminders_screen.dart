import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../config/api_config.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';

class RemindersScreen extends ConsumerStatefulWidget {
  const RemindersScreen({super.key});

  @override
  ConsumerState<RemindersScreen> createState() => _RemindersScreenState();
}

class _RemindersScreenState extends ConsumerState<RemindersScreen> {
  List<Map<String, dynamic>> _reminders = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadReminders();
  }

  Future<void> _loadReminders() async {
    final api = ref.read(apiServiceProvider);
    try {
      final response = await api.dio.get(ApiConfig.reminders);
      setState(() {
        _reminders = List<Map<String, dynamic>>.from(response.data);
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Reminders'),
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) {
              // Filter reminders by status
            },
            itemBuilder: (context) => [
              const PopupMenuItem(value: 'all', child: Text('All')),
              const PopupMenuItem(value: 'active', child: Text('Active')),
              const PopupMenuItem(value: 'snoozed', child: Text('Snoozed')),
              const PopupMenuItem(value: 'completed', child: Text('Completed')),
            ],
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showCreateReminderDialog,
        child: const Icon(Icons.add),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _reminders.isEmpty
              ? _buildEmptyState()
              : RefreshIndicator(
                  onRefresh: _loadReminders,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _reminders.length,
                    itemBuilder: (context, index) => _buildReminderCard(_reminders[index]),
                  ),
                ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.notifications_off_outlined, size: 64, color: Colors.grey[300]),
          const SizedBox(height: 16),
          Text('No reminders yet', style: TextStyle(color: Colors.grey[500], fontSize: 16)),
          const SizedBox(height: 8),
          Text('Tap + to create one, or ask the AI!', style: TextStyle(color: Colors.grey[400])),
        ],
      ),
    );
  }

  Widget _buildReminderCard(Map<String, dynamic> reminder) {
    final status = reminder['status'] ?? 'active';
    final isPersistent = reminder['is_persistent'] == true;
    final remindAt = DateTime.parse(reminder['remind_at']);
    final isOverdue = remindAt.isBefore(DateTime.now()) && status == 'active';

    Color statusColor;
    IconData statusIcon;
    switch (status) {
      case 'active':
        statusColor = isOverdue ? AppTheme.errorColor : AppTheme.primaryColor;
        statusIcon = isPersistent ? Icons.notifications_active : Icons.notifications;
        break;
      case 'snoozed':
        statusColor = AppTheme.warningColor;
        statusIcon = Icons.snooze;
        break;
      case 'completed':
        statusColor = AppTheme.successColor;
        statusIcon = Icons.check_circle;
        break;
      default:
        statusColor = Colors.grey;
        statusIcon = Icons.notifications_outlined;
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(statusIcon, color: statusColor, size: 24),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        reminder['title'],
                        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        DateFormat('MMM d, yyyy • HH:mm').format(remindAt),
                        style: TextStyle(
                          color: isOverdue ? AppTheme.errorColor : Colors.grey[600],
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
                if (isPersistent)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppTheme.warningColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Text(
                      'Persistent',
                      style: TextStyle(fontSize: 11, color: AppTheme.warningColor, fontWeight: FontWeight.w600),
                    ),
                  ),
              ],
            ),
            if (reminder['description'] != null) ...[
              const SizedBox(height: 8),
              Text(
                reminder['description'],
                style: TextStyle(color: Colors.grey[600], fontSize: 13),
              ),
            ],
            if (status == 'active') ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _markDone(reminder['id']),
                      icon: const Icon(Icons.check, size: 18),
                      label: const Text('Done'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.successColor,
                        padding: const EdgeInsets.symmetric(vertical: 8),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _snoozeReminder(reminder['id'], 10),
                      icon: const Icon(Icons.snooze, size: 18),
                      label: const Text('Snooze'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppTheme.warningColor,
                        padding: const EdgeInsets.symmetric(vertical: 8),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _markDone(String id) async {
    final api = ref.read(apiServiceProvider);
    await api.dio.post('${ApiConfig.reminders}/$id/done');
    _loadReminders();
  }

  Future<void> _snoozeReminder(String id, int minutes) async {
    final api = ref.read(apiServiceProvider);
    await api.dio.post('${ApiConfig.reminders}/$id/snooze', data: {'snooze_minutes': minutes});
    _loadReminders();
  }

  void _showCreateReminderDialog() {
    final titleController = TextEditingController();
    DateTime selectedDateTime = DateTime.now().add(const Duration(hours: 1));
    bool isPersistent = true;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) => Padding(
          padding: EdgeInsets.only(
            left: 24, right: 24, top: 24,
            bottom: MediaQuery.of(context).viewInsets.bottom + 24,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('New Reminder', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(height: 20),
              TextField(
                controller: titleController,
                decoration: const InputDecoration(
                  labelText: 'What to remember?',
                  prefixIcon: Icon(Icons.notifications_outlined),
                ),
                autofocus: true,
              ),
              const SizedBox(height: 16),
              ListTile(
                leading: const Icon(Icons.access_time),
                title: Text(DateFormat('MMM d, yyyy HH:mm').format(selectedDateTime)),
                onTap: () async {
                  final date = await showDatePicker(
                    context: context,
                    initialDate: selectedDateTime,
                    firstDate: DateTime.now(),
                    lastDate: DateTime.now().add(const Duration(days: 365)),
                  );
                  if (date != null) {
                    final time = await showTimePicker(
                      context: context,
                      initialTime: TimeOfDay.fromDateTime(selectedDateTime),
                    );
                    if (time != null) {
                      setModalState(() {
                        selectedDateTime = DateTime(date.year, date.month, date.day, time.hour, time.minute);
                      });
                    }
                  }
                },
              ),
              SwitchListTile(
                title: const Text('Persistent reminder'),
                subtitle: const Text('Keep reminding until marked done'),
                value: isPersistent,
                onChanged: (v) => setModalState(() => isPersistent = v),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () async {
                  if (titleController.text.isEmpty) return;
                  final api = ref.read(apiServiceProvider);
                  await api.dio.post(ApiConfig.reminders, data: {
                    'title': titleController.text,
                    'remind_at': selectedDateTime.toIso8601String(),
                    'is_persistent': isPersistent,
                  });
                  if (mounted) Navigator.of(context).pop();
                  _loadReminders();
                },
                child: const Text('Create Reminder'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
