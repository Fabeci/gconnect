import 'package:flutter/material.dart';

class CustomDrawer extends StatelessWidget {
  const CustomDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    return Drawer(
      child: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 24),
            _buildHeader(),
            const SizedBox(height: 24),
            _buildMenuItem(Icons.person_outline, 'Profil'),
            _buildMenuItem(Icons.favorite_border, 'Favoris', badge: '92'),
            _buildMenuItem(Icons.settings_outlined, 'Réglages'),
            _buildMenuItem(Icons.help_outline, 'Centre d’assistance'),
            _buildMenuItem(Icons.person_add_alt_1_outlined, 'Ajouter un autre compte'),
            const Spacer(),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 20),
              child: ElevatedButton(
                onPressed: () {},
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF3B5AFB),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(30),
                  ),
                  minimumSize: const Size.fromHeight(48),
                ),
                child: const Text(
                  'Deconnexion',
                  style: TextStyle(color: Colors.white),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return const Padding(
      padding: EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          CircleAvatar(
            radius: 28,
            backgroundImage: AssetImage('assets/images/home/user1.png'),
          ),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Fabrice djerabe',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
                SizedBox(height: 4),
                Text(
                  'Etudiant en informatique à l’UCAD\nDakar (Sénégal)',
                  style: TextStyle(fontSize: 13, color: Colors.grey),
                ),
                SizedBox(height: 8),
                Wrap(
                  spacing: 4,
                    children: [
                      Text(
                        '234 ',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      Text('Abonnements   '),
                      Text(
                        '102 ',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      Text('Abonnés'),
                    ],
                )
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMenuItem(IconData icon, String label, {String? badge}) {
    return ListTile(
      leading: Icon(icon, color: const Color(0xFF3B5AFB)),
      title: Row(
        children: [
          Text(label),
          if (badge != null) ...[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: Colors.grey.shade200,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                badge,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
              ),
            )
          ],
        ],
      ),
      onTap: () {
        // Navigation ou action
      },
    );
  }
}
