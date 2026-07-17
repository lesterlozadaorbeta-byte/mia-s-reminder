import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart' as fb;
import 'package:google_sign_in/google_sign_in.dart';

import '../config/api_config.dart';
import '../models/user_model.dart';
import '../services/api_service.dart';

/// Auth state - null means not authenticated
final authStateProvider = StateNotifierProvider<AuthNotifier, AsyncValue<UserModel?>>((ref) {
  return AuthNotifier(ref);
});

class AuthNotifier extends StateNotifier<AsyncValue<UserModel?>> {
  final Ref ref;
  final fb.FirebaseAuth _firebaseAuth = fb.FirebaseAuth.instance;

  AuthNotifier(this.ref) : super(const AsyncValue.data(null)) {
    _checkAuthState();
  }

  ApiService get _api => ref.read(apiServiceProvider);

  Future<void> _checkAuthState() async {
    final token = await _api.getAccessToken();
    if (token != null) {
      await fetchCurrentUser();
    }
  }

  Future<void> loginWithEmail(String email, String password) async {
    state = const AsyncValue.loading();
    try {
      final response = await _api.dio.post(ApiConfig.login, data: {
        'email': email,
        'password': password,
      });

      await _api.saveTokens(
        response.data['access_token'],
        response.data['refresh_token'],
      );

      await fetchCurrentUser();
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
      rethrow;
    }
  }

  Future<void> register(String email, String password, String fullName) async {
    state = const AsyncValue.loading();
    try {
      final response = await _api.dio.post(ApiConfig.register, data: {
        'email': email,
        'password': password,
        'full_name': fullName,
      });

      await _api.saveTokens(
        response.data['access_token'],
        response.data['refresh_token'],
      );

      await fetchCurrentUser();
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
      rethrow;
    }
  }

  Future<void> loginWithGoogle() async {
    state = const AsyncValue.loading();
    try {
      final googleUser = await GoogleSignIn().signIn();
      if (googleUser == null) {
        state = const AsyncValue.data(null);
        return;
      }

      final googleAuth = await googleUser.authentication;
      final credential = fb.GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      final userCredential = await _firebaseAuth.signInWithCredential(credential);
      final idToken = await userCredential.user?.getIdToken();

      if (idToken != null) {
        final response = await _api.dio.post(ApiConfig.oauth, data: {
          'firebase_token': idToken,
          'provider': 'google',
        });

        await _api.saveTokens(
          response.data['access_token'],
          response.data['refresh_token'],
        );

        await fetchCurrentUser();
      }
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
      rethrow;
    }
  }

  Future<void> loginWithApple() async {
    state = const AsyncValue.loading();
    try {
      final appleProvider = fb.AppleAuthProvider();
      final userCredential = await _firebaseAuth.signInWithProvider(appleProvider);
      final idToken = await userCredential.user?.getIdToken();

      if (idToken != null) {
        final response = await _api.dio.post(ApiConfig.oauth, data: {
          'firebase_token': idToken,
          'provider': 'apple',
        });

        await _api.saveTokens(
          response.data['access_token'],
          response.data['refresh_token'],
        );

        await fetchCurrentUser();
      }
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
      rethrow;
    }
  }

  Future<void> fetchCurrentUser() async {
    try {
      final response = await _api.dio.get(ApiConfig.me);
      final user = UserModel.fromJson(response.data);
      state = AsyncValue.data(user);
    } catch (e) {
      state = const AsyncValue.data(null);
    }
  }

  Future<void> logout() async {
    await _api.clearTokens();
    await _firebaseAuth.signOut();
    await GoogleSignIn().signOut();
    state = const AsyncValue.data(null);
  }
}
