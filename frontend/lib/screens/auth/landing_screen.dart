import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/app_theme.dart';

/// Public landing page - first thing everyone sees.
class LandingScreen extends StatelessWidget {
  const LandingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final isWide = size.width > 800;

    return Scaffold(
      body: SingleChildScrollView(
        child: Column(
          children: [
            _buildHero(context, isWide),
            _buildFeatures(context, isWide),
            _buildHowItWorks(context),
            _buildCTA(context),
            _buildFooter(context),
          ],
        ),
      ),
    );
  }

  Widget _buildHero(BuildContext context, bool isWide) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.symmetric(
        horizontal: isWide ? 80 : 24,
        vertical: isWide ? 100 : 60,
      ),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AppTheme.primaryColor.withOpacity(0.05),
            AppTheme.secondaryColor.withOpacity(0.05),
          ],
        ),
      ),
      child: isWide
          ? Row(
              children: [
                Expanded(child: _buildHeroText(context)),
                const SizedBox(width: 60),
                Expanded(child: _buildHeroVisual(context)),
              ],
            )
          : Column(
              children: [
                _buildHeroText(context),
                const SizedBox(height: 40),
                _buildHeroVisual(context),
              ],
            ),
    );
  }

  Widget _buildHeroText(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Nav bar
        Row(
          children: [
            const Icon(Icons.smart_toy_rounded, color: AppTheme.primaryColor, size: 32),
            const SizedBox(width: 8),
            Text(
              "Mia's Reminder",
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: AppTheme.primaryColor,
              ),
            ),
            const Spacer(),
            TextButton(
              onPressed: () => context.go('/auth/login'),
              child: const Text('Sign In'),
            ),
            const SizedBox(width: 8),
            ElevatedButton(
              onPressed: () => context.go('/auth/register'),
              child: const Text('Get Started Free'),
            ),
          ],
        ),
        const SizedBox(height: 60),
        Text(
          'Your AI-Powered\nLife Organizer',
          style: Theme.of(context).textTheme.displaySmall?.copyWith(
            fontWeight: FontWeight.bold,
            height: 1.2,
          ),
        ),
        const SizedBox(height: 20),
        Text(
          'Chat naturally to create reminders, schedule events, manage tasks, '
          'and plan your entire week. Mia is your AI assistant powered by GPT-4o with persistent '
          'reminders that won\'t let you forget.',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            color: Colors.grey[600],
            height: 1.6,
            fontSize: 17,
          ),
        ),
        const SizedBox(height: 32),
        Row(
          children: [
            ElevatedButton.icon(
              onPressed: () => context.go('/auth/register'),
              icon: const Icon(Icons.rocket_launch),
              label: const Text('Start Free'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
              ),
            ),
            const SizedBox(width: 16),
            OutlinedButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.play_circle_outline),
              label: const Text('See How It Works'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
              ),
            ),
          ],
        ),
        const SizedBox(height: 32),
        // Social proof
        Row(
          children: [
            const Icon(Icons.people, size: 18, color: Colors.grey),
            const SizedBox(width: 8),
            Text(
              'Join thousands organizing their lives with AI',
              style: TextStyle(color: Colors.grey[600], fontSize: 14),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildHeroVisual(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primaryColor.withOpacity(0.1),
            blurRadius: 40,
            offset: const Offset(0, 20),
          ),
        ],
        border: Border.all(color: Colors.grey[200]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Mock chat UI
          _buildMockMessage(true, 'Remind me to submit my assignment tomorrow at 8 AM'),
          const SizedBox(height: 12),
          _buildMockMessage(false,
            'Done! I\'ve created a persistent reminder:\n\n'
            '📌 Submit assignment\n'
            '⏰ Tomorrow, 8:00 AM\n'
            '🔁 Will keep reminding until you mark it done\n\n'
            'I\'ll also send you a Telegram notification. Anything else?'
          ),
          const SizedBox(height: 12),
          _buildMockMessage(true, 'Plan my study week for finals'),
          const SizedBox(height: 12),
          _buildMockMessage(false,
            'I\'ll create an optimized study schedule! Which subjects do you need to cover?'
          ),
        ],
      ),
    );
  }

  Widget _buildMockMessage(bool isUser, String text) {
    return Row(
      mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (!isUser)
          Container(
            margin: const EdgeInsets.only(right: 8),
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: AppTheme.primaryColor.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.smart_toy, size: 16, color: AppTheme.primaryColor),
          ),
        Flexible(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: isUser ? AppTheme.primaryColor : Colors.grey[100],
              borderRadius: BorderRadius.circular(14),
            ),
            child: Text(
              text,
              style: TextStyle(
                color: isUser ? Colors.white : Colors.black87,
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildFeatures(BuildContext context, bool isWide) {
    final features = [
      _FeatureItem(
        icon: Icons.chat_bubble_rounded,
        title: 'Natural Language AI',
        description: 'Just talk like you would to a friend. The AI understands and acts.',
        color: AppTheme.primaryColor,
      ),
      _FeatureItem(
        icon: Icons.notifications_active,
        title: 'Persistent Reminders',
        description: 'Won\'t stop reminding until you mark it done. Never miss anything.',
        color: AppTheme.warningColor,
      ),
      _FeatureItem(
        icon: Icons.calendar_month,
        title: 'Smart Calendar',
        description: 'Auto-schedules events, detects conflicts, suggests better times.',
        color: AppTheme.accentColor,
      ),
      _FeatureItem(
        icon: Icons.checklist_rounded,
        title: 'AI Task Lists',
        description: 'Breaks big goals into steps. Estimates time. Tracks progress.',
        color: AppTheme.successColor,
      ),
      _FeatureItem(
        icon: Icons.telegram,
        title: 'Telegram Bot',
        description: 'Get reminders, check schedule, chat with AI - all from Telegram.',
        color: const Color(0xFF0088CC),
      ),
      _FeatureItem(
        icon: Icons.schedule,
        title: 'AI Scheduler',
        description: 'Automatically plans your days, weeks, study sessions, and routines.',
        color: AppTheme.secondaryColor,
      ),
    ];

    return Container(
      padding: EdgeInsets.symmetric(horizontal: isWide ? 80 : 24, vertical: 60),
      child: Column(
        children: [
          Text(
            'Everything You Need',
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          Text(
            'One app to organize your entire life',
            style: TextStyle(color: Colors.grey[600], fontSize: 16),
          ),
          const SizedBox(height: 48),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: isWide ? 3 : 2,
              mainAxisSpacing: 20,
              crossAxisSpacing: 20,
              childAspectRatio: isWide ? 1.3 : 1.1,
            ),
            itemCount: features.length,
            itemBuilder: (context, index) => _buildFeatureCard(context, features[index]),
          ),
        ],
      ),
    );
  }

  Widget _buildFeatureCard(BuildContext context, _FeatureItem feature) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey[200]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: feature.color.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(feature.icon, color: feature.color, size: 24),
          ),
          const SizedBox(height: 16),
          Text(
            feature.title,
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16),
          ),
          const SizedBox(height: 8),
          Text(
            feature.description,
            style: TextStyle(color: Colors.grey[600], fontSize: 13, height: 1.4),
          ),
        ],
      ),
    );
  }

  Widget _buildHowItWorks(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 60),
      color: Colors.grey[50],
      child: Column(
        children: [
          Text(
            'How It Works',
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 48),
          Wrap(
            spacing: 32,
            runSpacing: 32,
            alignment: WrapAlignment.center,
            children: [
              _buildStep('1', 'Sign Up Free', 'Create your account in seconds'),
              _buildStep('2', 'Chat with AI', 'Tell it what you need in plain English'),
              _buildStep('3', 'Stay Organized', 'AI creates reminders, events & tasks for you'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStep(String number, String title, String subtitle) {
    return SizedBox(
      width: 220,
      child: Column(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: const BoxDecoration(
              color: AppTheme.primaryColor,
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                number,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 20),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 16)),
          const SizedBox(height: 8),
          Text(
            subtitle,
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey[600], fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildCTA(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 60),
      child: Column(
        children: [
          Text(
            'Ready to Get Organized?',
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          Text(
            'Free to use. No credit card required.',
            style: TextStyle(color: Colors.grey[600], fontSize: 16),
          ),
          const SizedBox(height: 32),
          ElevatedButton.icon(
            onPressed: () => context.go('/auth/register'),
            icon: const Icon(Icons.rocket_launch),
            label: const Text('Create Free Account'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 36, vertical: 18),
              textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFooter(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
      color: Colors.grey[900],
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.smart_toy_rounded, color: Colors.white, size: 24),
              const SizedBox(width: 8),
              const Text(
                "Mia's Reminder",
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 16),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Your intelligent personal life organizer.\nAvailable on Web, Android & iOS.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey[400], fontSize: 13),
          ),
          const SizedBox(height: 16),
          Text(
            "© 2024 Mia's Reminder. All rights reserved.",
            style: TextStyle(color: Colors.grey[600], fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _FeatureItem {
  final IconData icon;
  final String title;
  final String description;
  final Color color;

  _FeatureItem({
    required this.icon,
    required this.title,
    required this.description,
    required this.color,
  });
}
