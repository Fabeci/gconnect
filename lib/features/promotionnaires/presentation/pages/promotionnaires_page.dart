import 'package:flutter/material.dart';
import 'package:gconnect/core/widgets/bottom_navigation_widget.dart';
import 'package:gconnect/core/widgets/custom_sccafold_widget.dart';
import 'package:gconnect/core/widgets/drawer_navigation_widget.dart';
import '../widgets/promotionnaire_card.dart';
import '../../domain/entities/promotionnaire.dart';

class PromotionnairesPage extends StatelessWidget {
  const PromotionnairesPage({super.key});

  @override
  Widget build(BuildContext context) {
    final List<Promotionnaire> promotionnaires = [
      const Promotionnaire(
        name: 'Hassane Diop',
        subtitle: 'Infirmière à l’hôpital...',
        avatarUrl: 'assets/images/home/user1.png',
        backgroundUrl: 'https://i.pinimg.com/1200x/3d/09/55/3d0955d82338614f4810d41fe83ca3dd.jpg',
        relations: 12,
      ),
      const Promotionnaire(
        name: 'Hassane Diop',
        subtitle: 'Infirmière à l’hôpital...',
        avatarUrl: 'assets/images/home/user2.png',
        backgroundUrl: 'https://i.pinimg.com/1200x/3d/09/55/3d0955d82338614f4810d41fe83ca3dd.jpg',
        relations: 12,
      ),
      const Promotionnaire(
        name: 'Hassane Diop',
        subtitle: 'Infirmière à l’hôpital...',
        avatarUrl: 'assets/images/home/user3.png',
        backgroundUrl: 'https://img.freepik.com/photos-gratuite/mode-vie-sain-malbouffe-concept-mignon-femme-rousse-ne-peut-pas-resister-tentation-mordre-savoureux-ca_1258-127710.jpg',
        relations: 12,
      ),
      const Promotionnaire(
        name: 'Hassane Diop',
        subtitle: 'Infirmière à l’hôpital...',
        avatarUrl: 'assets/images/home/user4.png',
        backgroundUrl: 'https://static-cse.canva.com/blob/1982015/1600w-QJmAIFyfXww.jpg',
        relations: 12,
      ),
      const Promotionnaire(
        name: 'Hassane Diop',
        subtitle: 'Infirmière à l’hôpital...',
        avatarUrl: 'assets/images/home/user1.png',
        backgroundUrl: 'assets/images/home/user1.png',
        relations: 12,
      ),
      const Promotionnaire(
        name: 'Hassane Diop',
        subtitle: 'Infirmière à l’hôpital...',
        avatarUrl: 'assets/images/home/user2.png',
        backgroundUrl: 'https://timelinecovers.pro/facebook-cover/download/road-to-sunrise-facebook-cover.jpg',
        relations: 12,
      ),
    ];

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text('Promotionnaires'),
        centerTitle: true,
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
      ),
      body: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            // SearchBar
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              decoration: BoxDecoration(
                color: Colors.grey[200],
                borderRadius: BorderRadius.circular(32),
              ),
              child: const TextField(
                decoration: InputDecoration(
                  icon: Icon(Icons.search),
                  border: InputBorder.none,
                  hintText: 'Rechercher un promotionnaire...',
                ),
              ),
            ),
            const SizedBox(height: 16),

            // GridView of cards
            Expanded(
              child: GridView.builder(
                itemCount: promotionnaires.length,
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  childAspectRatio: 0.8,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                ),
                itemBuilder: (_, index) {
                  return PromotionnaireCard(promotionnaire: promotionnaires[index]);
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
