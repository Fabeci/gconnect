import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class PostItem extends StatelessWidget {
  const PostItem({super.key});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: Padding(
        padding: const EdgeInsets.all(4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: avatar, nom, date, options
            const Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  backgroundImage: AssetImage('assets/images/home/user2.png'),
                ),
                SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text("Seynabou Diagne", style: TextStyle(fontWeight: FontWeight.w600)),
                      Text("Étudiante à l’ESP de Dakar", style: TextStyle(color: Colors.grey, fontSize: 12)),
                      Text("Il y’a 2h", style: TextStyle(color: Colors.grey, fontSize: 12)),
                    ],
                  ),
                ),
                Icon(Icons.more_horiz, color: Colors.black54),
              ],
            ),
            const SizedBox(height: 12),

            // Contenu du post
            const Text("🎓 Rejoignez-nous pour un moment inoubliable ! 🎓"),
            const SizedBox(height: 4),
            const Text(
              "Chers alumni,\nLa journée de graduation approche... ",
              style: TextStyle(height: 1.4),
            ),
            const Text(
              "Afficher la suite",
              style: TextStyle(color: Colors.blue),
            ),

            const SizedBox(height: 12),

            // Image de l’événement
            ClipRRect(
              borderRadius: BorderRadius.circular(2),
              child: Image.asset('assets/images/posts/graduation_event.png'),
            ),

            const SizedBox(height: 12),

            // Réactions
            const Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(Icons.favorite, color: Colors.red),
                    SizedBox(width: 4),
                    Text("89"),
                  ],
                ),
                SizedBox(width: 16),
                Text("24 Commentaires"),
              ],
            ),

            const SizedBox(height: 12,),

            const Divider(height: 15),
            
            const SizedBox(height: 12,),
            // Actions
            Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              const _PostAction(icon: Icons.favorite_border, label: "J’aime"),
              GestureDetector(
                onTap: () => context.push('/comments'),
                child: const _PostAction(icon: Icons.comment_outlined, label: "Commenter"),
              ),
              const _PostAction(icon: Icons.share_outlined, label: "Partager"),
              const _PostAction(icon: Icons.send_outlined, label: "Envoyer"),
            ],
          ),
            
            const SizedBox(height: 12,),
          ],
        ),
      ),
    );
  }
}

class _PostAction extends StatelessWidget {
  final IconData icon;
  final String label;

  const _PostAction({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 20, color: Colors.black54),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(fontSize: 13)),
      ],
    );
  }
}
