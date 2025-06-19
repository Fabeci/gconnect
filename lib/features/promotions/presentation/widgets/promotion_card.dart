import 'package:flutter/material.dart';
import 'package:gconnect/features/promotions/data/models/promotion_model.dart';
import 'package:go_router/go_router.dart';

class PromotionCard extends StatelessWidget {
  final Promotion promotion;

  const PromotionCard({super.key, required this.promotion});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.all(18),
      color: Colors.white, // Pas de Card pour éviter les ombres et bords arrondis
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Ligne image + sous-titre
          Row(
            children: [
              Image.asset(
                'assets/icons/student.png', // remplace par ton icône de chapeau
                height: 30,
                width: 30,
              ),
              const SizedBox(width: 8),
              Text(
                promotion.subtitle,
                style: const TextStyle(color: Colors.grey),
              ),
            ],
          ),

          const SizedBox(height: 8),

          // Titre
          Text(
            promotion.title,
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),

          const SizedBox(height: 4),

          // Description
          Text(
            promotion.description,
            style: const TextStyle(color: Colors.black87),
          ),

          const SizedBox(height: 8),

          // Avatars + nombre membres
          Row(
            children: [
              ...List.generate(
                3,
                (index) => Padding(
                  padding: const EdgeInsets.only(right: 4),
                  child: const CircleAvatar(
                    radius: 10,
                    backgroundImage: AssetImage('assets/images/home/user1.png'),
                  ),
                ),
              ),
              Text("+${promotion.memberCount} membres"),
            ],
          ),
          
          const SizedBox(height: 12),
          // Bouton Rejoindre en haut à gauche
          ElevatedButton(
            onPressed: () {
              context.pushNamed(
                'promotion-detail',
                extra: promotion,
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.grey[100],
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              minimumSize: Size(0, 0), // annule la taille min
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              elevation: 0,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            child: const Text("Rejoindre", style: TextStyle(color: Colors.blue)),
          ),

          const SizedBox(height: 8),
        ],
      ),
    );
  }
}
