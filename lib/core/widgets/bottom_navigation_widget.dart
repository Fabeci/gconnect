import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:gconnect/core/constants/theme_constants.dart';
import 'package:go_router/go_router.dart'; // ⚡️


class BottomNavBar extends StatelessWidget {
  const BottomNavBar({super.key});

  @override
  Widget build(BuildContext context) {
    final String currentLocation = GoRouter.of(context).routerDelegate.currentConfiguration.fullPath;

    return BottomAppBar(
      shape: const CircularNotchedRectangle(),
      notchMargin: 8,
      color: Colors.white,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _BottomNavItem(
            assetPath: 'assets/icons/home.svg',
            label: "Accueil",
            onTap: () => context.go('/home'),
            isActive: currentLocation == '/home',
          ),
          _BottomNavItem(
            assetPath: 'assets/icons/lightbulb.svg',
            label: "Opportunités",
            onTap: () => context.go('/opportunites'),
            isActive: currentLocation == '/opportunites',
          ),
          const SizedBox(width: 40), // espace pour le FAB
          _BottomNavItem(
            assetPath: 'assets/icons/cap.svg',
            label: "Etablissement",
            onTap: () => context.go('/establishment'),
            isActive: currentLocation == '/establishment',
          ),
          _BottomNavItem(
            assetPath: 'assets/icons/users.svg',
            label: "Promo",
            onTap: () => context.go('/promotions'),
            isActive: currentLocation == '/promotions',
          ),
        ],
      ),
    );
  }
}

class _BottomNavItem extends StatelessWidget {
  final String assetPath;
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  const _BottomNavItem({
    super.key,
    required this.assetPath,
    required this.label,
    required this.onTap,
    required this.isActive,
  });

  @override
  Widget build(BuildContext context) {
    final color = isActive ? ThemeConstants.orangeColor : Colors.grey;

    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 15),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SvgPicture.asset(
              assetPath,
              width: 18,
              height: 18,
              color: color,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
