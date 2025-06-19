import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:gconnect/core/constants/theme_constants.dart';
import 'package:gconnect/core/models/bullet_point.dart';
import 'package:gconnect/core/widgets/logo_widget.dart';
import 'package:gconnect/features/onboarding/presentation/onboarding_data.dart';

class OnboardingContent extends StatelessWidget {
  final OnboardingInfo data;

  const OnboardingContent({super.key, required this.data});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      height: double.infinity,
      color: Colors.white, // 👈 important pour éviter l'effet transparent entre pages
      child: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 40),
            const LogoWidget(),
            const SizedBox(height: 30),

            // Titre
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10.0),
              child: Text(
                data.title,
                style: Theme.of(context)
                    .textTheme
                    .headlineSmall
                    ?.copyWith(fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
            ),

            const SizedBox(height: 12),

            // Description
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10.0),
              child: Text(
                data.description,
                style: Theme.of(context).textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
            ),

            const SizedBox(height: 24),

            // Illustration
            if (data.imageAsset != null) ...[
              const SizedBox(height: 24),
              Image.asset(
                data.imageAsset!,
                height: 250,
                fit: BoxFit.contain,
              ),
            ],

            // Liste à puces (si présente)
            if (data.bulletPoints != null)
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 20),
                  children: data.bulletPoints!
                      .map((bp) => buildBulletPoint(bp))
                      .toList(),
                ),
              )
            else
              const Spacer(),

            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget buildBulletPoint(BulletPoint bullet) {
  return Padding(
    padding: const EdgeInsets.symmetric(vertical: 10.0, horizontal: 15.0),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SvgPicture.asset(
          bullet.iconAsset,
          width: 30,
          height: 30,
        ),
        const SizedBox(height: 12),
        Text(
          bullet.title,
          style: ThemeConstants.headingStyle.copyWith(fontSize: 18),
          // textAlign: TextAlign.center,
        ),
        const SizedBox(height: 4),
        Text(
          bullet.description,
          style: ThemeConstants.bodyStyle,
          // textAlign: TextAlign.center,
        ),
      ],
    ),
  );
}

}
