import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/api_config.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';

class TodoScreen extends ConsumerStatefulWidget {
  const TodoScreen({super.key});

  @override
  ConsumerState<TodoScreen> createState() => _TodoScreenState();
}

class _TodoScreenState extends ConsumerState<TodoScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  List<Map<String, dynamic>> _todos = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadTodos();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadTodos() async {
    final api = ref.read(apiServiceProvider);
    try {
      final response = await api.dio.get(ApiConfig.todos);
      setState(() {
        _todos = List<Map<String, dynamic>>.from(response.data['todos'] ?? []);
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  List<Map<String, dynamic>> get _pendingTodos =>
      _todos.where((t) => t['is_completed'] != true).toList();

  List<Map<String, dynamic>> get _completedTodos =>
      _todos.where((t) => t['is_completed'] == true).toList();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Tasks'),
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(text: 'All (${_todos.length})'),
            Tab(text: 'Pending (${_pendingTodos.length})'),
            Tab(text: 'Done (${_completedTodos.length})'),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showCreateTodoDialog,
        child: const Icon(Icons.add),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabController,
              children: [
                _buildTodoList(_todos),
                _buildTodoList(_pendingTodos),
                _buildTodoList(_completedTodos),
              ],
            ),
    );
  }

  Widget _buildTodoList(List<Map<String, dynamic>> todos) {
    if (todos.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.check_circle_outline, size: 64, color: Colors.grey[300]),
            const SizedBox(height: 16),
            Text('No tasks here', style: TextStyle(color: Colors.grey[500])),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadTodos,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: todos.length,
        itemBuilder: (context, index) => _buildTodoTile(todos[index]),
      ),
    );
  }

  Widget _buildTodoTile(Map<String, dynamic> todo) {
    final isCompleted = todo['is_completed'] == true;
    final priorityColors = {
      1: AppTheme.priorityUrgent,
      2: AppTheme.priorityHigh,
      3: AppTheme.priorityMedium,
      4: AppTheme.priorityLow,
    };
    final color = priorityColors[todo['priority']] ?? Colors.grey;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Dismissible(
        key: Key(todo['id']),
        direction: DismissDirection.endToStart,
        background: Container(
          alignment: Alignment.centerRight,
          padding: const EdgeInsets.only(right: 20),
          color: Colors.red,
          child: const Icon(Icons.delete, color: Colors.white),
        ),
        onDismissed: (_) => _deleteTodo(todo['id']),
        child: ListTile(
          leading: GestureDetector(
            onTap: () => _toggleTodo(todo['id'], !isCompleted),
            child: Icon(
              isCompleted ? Icons.check_circle : Icons.radio_button_unchecked,
              color: isCompleted ? AppTheme.successColor : color,
            ),
          ),
          title: Text(
            todo['title'],
            style: TextStyle(
              fontWeight: FontWeight.w500,
              decoration: isCompleted ? TextDecoration.lineThrough : null,
              color: isCompleted ? Colors.grey : null,
            ),
          ),
          subtitle: todo['due_date'] != null
              ? Text(
                  'Due: ${_formatDate(todo['due_date'])}',
                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                )
              : null,
          trailing: _buildPriorityBadge(todo['priority']),
        ),
      ),
    );
  }

  Widget _buildPriorityBadge(int? priority) {
    final labels = {1: 'P1', 2: 'P2', 3: 'P3', 4: 'P4'};
    final colors = {
      1: AppTheme.priorityUrgent,
      2: AppTheme.priorityHigh,
      3: AppTheme.priorityMedium,
      4: AppTheme.priorityLow,
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: (colors[priority] ?? Colors.grey).withOpacity(0.1),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        labels[priority] ?? 'P3',
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: colors[priority] ?? Colors.grey,
        ),
      ),
    );
  }

  Future<void> _toggleTodo(String id, bool completed) async {
    final api = ref.read(apiServiceProvider);
    try {
      if (completed) {
        await api.dio.post('${ApiConfig.todos}/$id/complete');
      } else {
        await api.dio.patch('${ApiConfig.todos}/$id', data: {'is_completed': false});
      }
      _loadTodos();
    } catch (e) {
      // Handle error
    }
  }

  Future<void> _deleteTodo(String id) async {
    final api = ref.read(apiServiceProvider);
    try {
      await api.dio.delete('${ApiConfig.todos}/$id');
      _loadTodos();
    } catch (e) {
      // Handle error
    }
  }

  String _formatDate(String iso) {
    final dt = DateTime.parse(iso);
    return '${dt.month}/${dt.day}/${dt.year}';
  }

  void _showCreateTodoDialog() {
    final titleController = TextEditingController();
    int selectedPriority = 3;

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
              Text('New Task', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(height: 20),
              TextField(
                controller: titleController,
                decoration: const InputDecoration(
                  labelText: 'Task title',
                  prefixIcon: Icon(Icons.check_circle_outline),
                ),
                autofocus: true,
              ),
              const SizedBox(height: 16),
              Text('Priority', style: TextStyle(fontWeight: FontWeight.w500, color: Colors.grey[700])),
              const SizedBox(height: 8),
              SegmentedButton<int>(
                segments: const [
                  ButtonSegment(value: 1, label: Text('Urgent')),
                  ButtonSegment(value: 2, label: Text('High')),
                  ButtonSegment(value: 3, label: Text('Medium')),
                  ButtonSegment(value: 4, label: Text('Low')),
                ],
                selected: {selectedPriority},
                onSelectionChanged: (p) => setModalState(() => selectedPriority = p.first),
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () async {
                  if (titleController.text.isEmpty) return;
                  final api = ref.read(apiServiceProvider);
                  await api.dio.post(ApiConfig.todos, data: {
                    'title': titleController.text,
                    'priority': selectedPriority,
                  });
                  if (mounted) Navigator.of(context).pop();
                  _loadTodos();
                },
                child: const Text('Create Task'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
