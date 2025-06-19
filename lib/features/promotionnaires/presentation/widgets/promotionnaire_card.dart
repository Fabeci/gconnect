import 'package:flutter/material.dart';
import '../../domain/entities/promotionnaire.dart';

class PromotionnaireCard extends StatelessWidget {
  final Promotionnaire promotionnaire;

  const PromotionnaireCard({super.key, required this.promotionnaire});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        color: Colors.white,
        boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 4)],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header with background and avatar
          SizedBox(
            height: 40,
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                ClipRRect(
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(12),
                    topRight: Radius.circular(12),
                  ),
                  child: Image.network(
                    promotionnaire.backgroundUrl,
                    width: double.infinity,
                    height: 70,
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) => const SizedBox(
                      height: 70,
                      child: Center(child: Icon(Icons.broken_image)),
                    ),
                    loadingBuilder: (context, child, loadingProgress) {
                      if (loadingProgress == null) return child;
                      return const SizedBox(
                        height: 70,
                        child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
                      );
                    },
                  ),
                ),
                Positioned(
                  right: 4,
                  top: 4,
                  child: CircleAvatar(
                    radius: 12,
                    backgroundColor: Colors.white,
                    child: const Icon(Icons.close, size: 14),
                  ),
                ),
                Positioned(
                  left: 12,
                  bottom: -20,
                  child: CircleAvatar(
                    radius: 20,
                    backgroundImage: AssetImage(promotionnaire.avatarUrl),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24), // espace après l'avatar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text(
              promotionnaire.name,
              style: const TextStyle(fontWeight: FontWeight.bold),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: Text(
              promotionnaire.subtitle,
              style: const TextStyle(color: Colors.grey, fontSize: 12),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(height: 8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(
              children: [
                const CircleAvatar(
                  radius: 10,
                  backgroundImage: AssetImage('assets/images/home/user3.png'),
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    '+${promotionnaire.relations} relations',
                    style: const TextStyle(fontSize: 12),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Center(
            child: TextButton(
              onPressed: () {},
              style: TextButton.styleFrom(
                foregroundColor: Colors.blue,
                padding: const EdgeInsets.symmetric(horizontal: 20),
                backgroundColor: Colors.blue[50],
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                ),
              ),
              child: const Text('Voir profil'),
            ),
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }
}
