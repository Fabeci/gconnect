import 'package:flutter/material.dart';
import 'package:gconnect/features/chats/presentation/pages/discussions_page.dart';
import 'package:gconnect/features/chats/presentation/pages/new_discussion_page.dart';
import 'package:gconnect/features/comments/presentation/pages/comment_page.dart';
import 'package:gconnect/features/establishment/domain/entities/establishment.dart';
import 'package:gconnect/features/establishment/presentation/pages/establishment_detail_page.dart';
import 'package:gconnect/features/establishment/presentation/pages/establishments_page.dart';
import 'package:gconnect/features/home/presentations/pages/home_load_screen.dart';
import 'package:gconnect/features/home/presentations/pages/home_page.dart';
import 'package:gconnect/features/promotionnaires/presentation/pages/promotionnaires_page.dart';
import 'package:gconnect/features/promotions/data/models/promotion_model.dart';
import 'package:gconnect/features/promotions/presentation/pages/promotion_detail_page.dart';
import 'package:gconnect/features/promotions/presentation/pages/promotions_page.dart';
import 'package:go_router/go_router.dart';
import 'package:gconnect/features/auth/presentation/pages/login_page.dart';
import 'package:gconnect/features/auth/presentation/pages/register_page_step1.dart';
import 'package:gconnect/features/auth/presentation/pages/register_page_step2.dart';
import 'package:gconnect/features/auth/presentation/pages/register_selector.dart';
import 'package:gconnect/features/onboarding/presentation/pages/onboarding_page.dart';

class AppRouter {
  static final GoRouter router = GoRouter(
    initialLocation: '/onboarding',
    routes: [
      GoRoute(
        path: '/onboarding',
        name: 'onboarding',
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (context, state) => const LoginPage(),
      ),
      GoRoute(
        path: '/register',
        name: 'register_selector',
        builder: (context, state) => const RegisterSelectorPage(),
      ),
      GoRoute(
        path: '/register-step1',
        name: 'register_step1',
        builder: (context, state) => const RegisterStep1Page(),
      ),
      GoRoute(
        path: '/register-step2',
        name: 'register_step2',
        builder: (context, state) => const RegisterStep2Page(),
      ),
      GoRoute(
        path: '/home-loading',
        name: 'home_loading',
        // builder: (context, state) => const HomeLoadingPage(),
        builder: (BuildContext context, GoRouterState state) {
          return const HomeLoadingPage();
        },
      ),
      GoRoute(
        path: '/home',
        name: 'home',
        builder: (BuildContext context, GoRouterState state) {
          return const HomePage();
        },
      ),
      GoRoute(
        path: '/comments',
        name: 'comments',
        builder: (context, state) => const CommentPage(),
      ),
      GoRoute(
        path: '/promotions',
        name: 'promotions',
        builder: (BuildContext context, GoRouterState state) {
          return PromotionsPage();
        },
      ),
      GoRoute(
        path: '/promotionnaires',
        name: 'promotionnaires',
        builder: (BuildContext context, GoRouterState state) {
          return const PromotionnairesPage();
        },
      ),
      GoRoute(
        path: '/promotion-detail',
        name: 'promotion-detail',
        builder: (context, state) {
          final promotion = state.extra as Promotion;
          return PromotionDetailPage(promotion: promotion);
        },
      ),
      // ######################### Etablissement ##############################
      GoRoute(
        path: '/establishment',
        name: 'establishment',
        builder: (context, state) {
          return EstablishmentsPage();
        },
      ),

      GoRoute(
        path: '/establishment-detail',
        name: 'establishment-detail',
        builder: (context, state) {
          final establishment = state.extra as Establishment;
          return EstablishmentDetailPage(establishment: establishment);
        },
      ),

      GoRoute(
        path: '/discussions',
        name: 'discussions',
        builder: (context, state) => const DiscussionsPage(),
      ),

      GoRoute(
        path: '/new-discussion',
        name: 'new-discussion',
        builder: (context, state) => const NewDiscussionPage(),
      ),
    ],
  );
}
