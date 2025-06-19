import 'package:flutter/material.dart';

class ProfileCard extends StatelessWidget {
  final String name;
  final int relations;
  final String avatarPath;
  final List<String> relationAvatars;
  final VoidCallback onRemove;

  const ProfileCard({
    super.key,
    required this.name,
    required this.relations,
    required this.avatarPath,
    required this.relationAvatars,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 150,
      // padding: const EdgeInsets.all(12),
      margin: const EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        color: Colors.white,
      ),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Stack(
              clipBehavior: Clip.none,
              children: [
                // ✅ Fond dégradé uniquement en haut, sans coins arrondis en bas
                Container(
                  height: 60,
                  decoration: const BoxDecoration(
                    borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(12),
                      topRight: Radius.circular(12),
                    ),
                    gradient: LinearGradient(
                      colors: [Color(0xFFB0E0FF), Color(0xFFCCE8FF)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                  ),
                ),

                // ✅ Avatar à cheval sur le fond dégradé et le bas
                Positioned(
                  top: 22, // ajuste la hauteur de "chevauchement"
                  left: 15,
                  child: CircleAvatar(
                    backgroundImage: AssetImage(avatarPath),
                    radius: 28,
                  ),
                ),

                // ✅ Bouton de suppression (croix)
                Positioned(
                  top: 4,
                  right: 4,
                  child: GestureDetector(
                    onTap: onRemove,
                    child: const CircleAvatar(
                      radius: 14,
                      backgroundColor: Colors.white,
                      child: Icon(Icons.close, size: 18, color: Colors.grey),
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 22),
            Text(name, style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 14)),
            const SizedBox(height: 10),
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: Wrap(
                alignment: WrapAlignment.center,
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 4,
                children: [
                  ...relationAvatars.take(3).map((path) => Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 2),
                    child: CircleAvatar(
                      backgroundImage: AssetImage(path),
                      radius: 12,
                    ),
                  )),
                  const SizedBox(width: 4),
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 80),
                    child: Text(
                      "+$relations relations",
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.grey),
                    ),
                  )
                ],
              ),
            ),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: ElevatedButton(
                onPressed: () {},
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFF0F4FF),
                  foregroundColor: const Color(0xFF3366FF),
                  minimumSize: const Size(double.infinity, 36),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  padding: EdgeInsets.zero,
                  elevation: 0,
                  textStyle: const TextStyle(fontWeight: FontWeight.w500),
                ),
                child: const Text("Voir profil"),
              ),
            )
          ],
        ),
      ),
    );
  }
}
