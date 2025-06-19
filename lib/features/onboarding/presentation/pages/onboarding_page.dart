import 'package:flutter/material.dart';
import 'package:gconnect/core/constants/theme_constants.dart';
import 'package:gconnect/features/onboarding/presentation/onboarding_data.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:liquid_swipe/liquid_swipe.dart';
import '../widgets/onboarding_content.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final LiquidController _liquidController = LiquidController();
  int _currentPage = 0;

  void _onNext() {
    if (_currentPage < onboardingPages.length - 1) {
      _liquidController.animateToPage(page: _currentPage + 1);
    } else {
      context.go('/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool isLastPage = _currentPage == onboardingPages.length - 1;

    return Scaffold(
      body: Stack(
        children: [
          // ✅ LiquidSwipe sans builder
          LiquidSwipe(
            pages: onboardingPages
                .map((data) => OnboardingContent(data: data))
                .toList(),
            positionSlideIcon: 0.8,
            slideIconWidget: const Icon(Icons.arrow_back_ios),
            waveType: WaveType.liquidReveal,
            enableSideReveal: true,
            fullTransitionValue: 400,
            liquidController: _liquidController,
            onPageChangeCallback: (index) {
              setState(() {
                _currentPage = index;
              });
            },
          ),

          // ✅ Boutons et indicateurs
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: Container(
              padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Indicateurs
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(
                      onboardingPages.length,
                      (index) => AnimatedContainer(
                        duration: const Duration(milliseconds: 250),
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        height: 3,
                        width: 30,
                        decoration: BoxDecoration(
                          color: _currentPage == index
                              ? ThemeConstants.primaryColor
                              : Colors.grey.shade300,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  // Bouton principal
                  SizedBox(
                    width: double.infinity,
                    height: 44,
                    child: ElevatedButton(
                      onPressed: _onNext,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: ThemeConstants.primaryColor,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(28),
                        ),
                      ),
                      child: Text(
                        isLastPage ? 'Connexion' : 'Suivant',
                        style: const TextStyle(fontSize: 16),
                      ),
                    ),
                  ),

// Bouton secondaire animé
                  AnimatedSwitcher(
                    duration: const Duration(milliseconds: 500),
                    transitionBuilder:
                        (Widget child, Animation<double> animation) {
                      final offsetAnimation = Tween<Offset>(
                        begin: const Offset(0, 0.2),
                        end: Offset.zero,
                      ).animate(animation);
                      return FadeTransition(
                        opacity: animation,
                        child: SlideTransition(
                            position: offsetAnimation, child: child),
                      );
                    },
                    child: isLastPage
                        ? Padding(
                            padding: const EdgeInsets.only(top: 12),
                            key:
                                const ValueKey('register_button'), // clé unique
                            child: SizedBox(
                              width: double.infinity,
                              height: 44,
                              child: OutlinedButton(
                                onPressed: () => context.go('/register'),
                                style: OutlinedButton.styleFrom(
                                  side: const BorderSide(
                                      color: ThemeConstants.primaryColor),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(28),
                                  ),
                                ),
                                child: const Text(
                                  "S'inscrire",
                                  style: TextStyle(
                                    color: ThemeConstants.primaryColor,
                                    fontSize: 16,
                                  ),
                                ),
                              ),
                            ),
                          )
                        : const SizedBox.shrink(),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
