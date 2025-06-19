import 'package:flutter/material.dart';
import 'package:gconnect/features/promotionnaires/domain/entities/promotionnaire.dart';
import 'package:gconnect/features/promotionnaires/presentation/widgets/promotionnaire_card.dart';

class MembersTab extends StatelessWidget {
  const MembersTab({super.key});

  @override
  Widget build(BuildContext context) {
    // Exemple de données simulées
    final List<Promotionnaire> promotionnaires = List.generate(
      10,
      (index) => Promotionnaire(
        name: 'Promotionnaire ${index + 1}',
        subtitle: index == 0 ? 'Délégué de classe' : 'Étudiant',
        avatarUrl: 'assets/images/home/user1.png',
        backgroundUrl: 'https://timelinecovers.pro/facebook-cover/download/road-to-sunrise-facebook-cover.jpg', // ou une image réseau réelle
        relations: 5 + index,
      ),
    );

    return Padding(
      padding: const EdgeInsets.all(16),
      child: GridView.builder(
        itemCount: promotionnaires.length,
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 0.75,
        ),
        itemBuilder: (context, index) {
          return PromotionnaireCard(promotionnaire: promotionnaires[index]);
        },
      ),
    );
  }
}
