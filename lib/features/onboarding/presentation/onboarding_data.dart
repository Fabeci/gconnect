import 'package:gconnect/core/models/bullet_point.dart';

class OnboardingInfo {
  final String title;
  final String description;
  final String? imageAsset;
  final List<BulletPoint>? bulletPoints;

  OnboardingInfo({
    required this.title,
    required this.description,
    this.imageAsset,
    this.bulletPoints,
  });
}

final List<OnboardingInfo> onboardingPages = [
  OnboardingInfo(
    title: "Bienvenue sur G-Connect",
    description:
        "une plateforme qui connecte étudiants, alumni et entreprises pour des opportunités professionnelles enrichissantes.",
    imageAsset: "assets/images/onboarding/onboarding_0.png",
  ),
  OnboardingInfo(
    title: "Qu’est-ce que vous pouvez faire ?",
    description:
        "Élargissez votre réseau et trouvez les meilleures opportunités adaptées à vos besoins.",
    bulletPoints: [
      BulletPoint(
        iconAsset: "assets/icons/post.svg",
        title: "Postez ou recherchez des opportunités",
        description: "Offres d’emploi, stages, formations, mentorats.",
      ),
      BulletPoint(
        iconAsset: "assets/icons/search.svg",
        title: "Recherchez des talents",
        description: "Trouvez étudiants et alumni qualifiés.",
      ),
      BulletPoint(
        iconAsset: "assets/icons/connect.svg",
        title: "Restez connecté",
        description: "Établissez des liens avec les promotions et alumni.",
      ),
    ],
  ),

  OnboardingInfo(
    title: "Prêt à commencer ?",
    description:
        "Créez votre compte pour explorer toutes les fonctionnalités et saisir les opportunités.",
    imageAsset: "assets/images/onboarding/onboarding_1.png",
  ),
];
