import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../config/api_config.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';

class AlarmsScreen extends ConsumerStatefulWidget {
  const AlarmsScreen({super.key});

  @override
  ConsumerState<AlarmsScreen> createState() => _AlarmsScreenState();
}

class _AlarmsScreenState extends ConsumerState<AlarmsScreen> {
  List<Map<String, dynamic>> _alarms = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadAlarms();
  }

  Future<void> _loadAlarms() async {
    final api = ref.read(apiServiceProvider);
    try {
      final response = await api.dio.get(ApiConfig.alarms);
      setState(() {
        _alarms = List<Map<String, dynamic>>.from(response.data);
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Alarms')),
      floatingActionButton: FloatingActionButton(
        onPressed: _showCreateAlarmDialog,
        child: const Icon(Icons.add_alarm),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _alarms.isEmpty
              ? _buildEmptyState()
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: _alarms.length,
                  itemBuilder: (context, index) => _buildAlarmCard(_alarms[index]),
                ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.alarm_off, size: 64, color: Colors.grey[300]),
          const SizedBox(height: 16),
          Text('No alarms set', style: TextStyle(color: Colors.grey[500], fontSize: 16)),
        ],
      ),
    );
  }

  Widget _buildAlarmCard(Map<String, dynamic> alarm) {
    final isActive = alarm['is_active'] == true;
    final alarmTime = DateTime.parse(alarm['alarm_time']);
    final repeatDays = List<int>.from(alarm['repeat_days'] ?? []);
    final dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    IconData typeIcon;
    switch (alarm['alarm_type']) {
      case 'wake_up':
        typeIcon = Icons.wb_sunny;
        break;
      case 'medication':
        typeIcon = Icons.medication;
        break;
      case 'study':
        typeIcon = Icons.school;
        break;
      default:
        typeIcon = Icons.alarm;
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
                Icon(typeIcon, color: isActive ? AppTheme.primaryColor : Colors.grey),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        alarm['title'],
                        style: TextStyle(
                          fontWeight: FontWeight.w500,
                          color: isActive ? null : Colors.grey,
                        ),
                      ),
                      Text(
                        DateFormat('HH:mm').format(alarmTime),
                        style: TextStyle(
                          fontSize: 32,
                          fontWeight: FontWeight.w300,
                          color: isActive ? null : Colors.grey,
                        ),
                      ),
                    ],
                  ),
                ),
                Switch(
                  value: isActive,
                  onChanged: (v) => _toggleAlarm(alarm['id']),
                  activeColor: AppTheme.primaryColor,
                ),
              ],
            ),
            if (repeatDays.isNotEmpty) ...[
              const SizedBox(height: 8),
              Row(
                children: List.generate(7, (i) {
                  final isSelected = repeatDays.contains(i);
                  return Container(
                    margin: const EdgeInsets.only(right: 4),
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      color: isSelected ? AppTheme.primaryColor.withOpacity(0.1) : null,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: isSelected ? AppTheme.primaryColor : Colors.grey[300]!,
                      ),
                    ),
                    child: Center(
                      child: Text(
                        dayNames[i][0],
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: isSelected ? AppTheme.primaryColor : Colors.grey,
                        ),
                      ),
                    ),
                  );
                }),
              ),
            ],
            if (alarm['label'] != null) ...[
              const SizedBox(height: 8),
              Chip(
                label: Text(alarm['label'], style: const TextStyle(fontSize: 12)),
                visualDensity: VisualDensity.compact,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _toggleAlarm(String id) async {
    final api = ref.read(apiServiceProvider);
    await api.dio.post('${ApiConfig.alarms}/$id/toggle');
    _loadAlarms();
  }

  void _showCreateAlarmDialog() {
    final titleController = TextEditingController();
    TimeOfDay selectedTime = TimeOfDay.now();
    String alarmType = 'general';
    List<int> repeatDays = [];

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
              Text('New Alarm', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(height: 20),
              TextField(
                controller: titleController,
                decoration: const InputDecoration(
                  labelText: 'Alarm name',
                  prefixIcon: Icon(Icons.alarm),
                ),
              ),
              const SizedBox(height: 16),
              GestureDetector(
                onTap: () async {
                  final time = await showTimePicker(
                    context: context,
                    initialTime: selectedTime,
                  );
                  if (time != null) {
                    setModalState(() => selectedTime = time);
                  }
                },
                child: Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.grey[300]!),
                  ),
                  child: Center(
                    child: Text(
                      selectedTime.format(context),
                      style: const TextStyle(fontSize: 36, fontWeight: FontWeight.w300),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              // Alarm type
              DropdownButtonFormField<String>(
                value: alarmType,
                decoration: const InputDecoration(labelText: 'Type'),
                items: const [
                  DropdownMenuItem(value: 'general', child: Text('General')),
                  DropdownMenuItem(value: 'wake_up', child: Text('Wake Up')),
                  DropdownMenuItem(value: 'medication', child: Text('Medication')),
                  DropdownMenuItem(value: 'study', child: Text('Study')),
                ],
                onChanged: (v) => setModalState(() => alarmType = v!),
              ),
              const SizedBox(height: 16),
              // Repeat days
              Text('Repeat', style: TextStyle(color: Colors.grey[700], fontWeight: FontWeight.w500)),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: ['M', 'T', 'W', 'T', 'F', 'S', 'S'].asMap().entries.map((entry) {
                  final isSelected = repeatDays.contains(entry.key);
                  return GestureDetector(
                    onTap: () => setModalState(() {
                      isSelected ? repeatDays.remove(entry.key) : repeatDays.add(entry.key);
                    }),
                    child: Container(
                      width: 38,
                      height: 38,
                      decoration: BoxDecoration(
                        color: isSelected ? AppTheme.primaryColor : null,
                        borderRadius: BorderRadius.circular(19),
                        border: Border.all(
                          color: isSelected ? AppTheme.primaryColor : Colors.grey[300]!,
                        ),
                      ),
                      child: Center(
                        child: Text(
                          entry.value,
                          style: TextStyle(
                            color: isSelected ? Colors.white : Colors.grey[600],
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () async {
                  final now = DateTime.now();
                  final alarmDateTime = DateTime(
                    now.year, now.month, now.day,
                    selectedTime.hour, selectedTime.minute,
                  );
                  final api = ref.read(apiServiceProvider);
                  await api.dio.post(ApiConfig.alarms, data: {
                    'title': titleController.text.isEmpty ? 'Alarm' : titleController.text,
                    'alarm_time': alarmDateTime.toIso8601String(),
                    'alarm_type': alarmType,
                    'is_recurring': repeatDays.isNotEmpty,
                    'repeat_days': repeatDays,
                  });
                  if (mounted) Navigator.of(context).pop();
                  _loadAlarms();
                },
                child: const Text('Set Alarm'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
