import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class NewDiscussionPage extends StatelessWidget {
  const NewDiscussionPage({super.key});

  @override
  Widget build(BuildContext context) {
    final frequentContacts = [
      {'name': 'Seynabou Diagne', 'image': 'assets/images/home/user1.png'},
      {'name': 'Alpha Conde', 'image': 'assets/images/home/user2.png'},
    ];

    final allContacts = [
      {'name': 'Seynabou Diop', 'image': 'assets/images/home/user3.png'},
      {'name': 'Mor Niang', 'image': 'assets/images/home/user4.png'},
      {'name': 'Assane Coulibay', 'image': 'assets/images/home/user1.png'},
      {'name': 'Birima Diop', 'image': 'assets/images/home/user2.png'},
      {'name': 'Khady Sow', 'image': 'assets/images/home/user3.png'},
    ];

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.black),
          onPressed: () => context.pop(),
        ),
        title: const Text(
          'Nouvelle discussion',
          style: TextStyle(color: Colors.black),
        ),
        backgroundColor: Colors.white,
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        children: [
          const SizedBox(height: 8),
          _buildSearchBar(),
          const SizedBox(height: 16),
          _buildActionButton(
            icon: Icons.person_add,
            label: 'Ajouter un nouveau contact',
            onTap: () {},
          ),
          _buildActionButton(
            icon: Icons.group_add,
            label: 'Créer un nouveau groupe',
            onTap: () {},
          ),
          const SizedBox(height: 24),
          const Text(
            'Contacts fréquents',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          ...frequentContacts.map((contact) => _buildContactItem(contact)),
          const SizedBox(height: 24),
          const Text(
            'Tous les contacts',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const Divider(),
          ...allContacts.map((contact) => _buildContactItem(contact)),
        ],
      ),
    );
  }

  Widget _buildSearchBar() {
    return const TextField(
      decoration: InputDecoration(
        hintText: 'Rechercher un nom ou un numéro',
        prefixIcon: Icon(Icons.search),
        filled: true,
        fillColor: Color(0xFFF0F0F0),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(24)),
          borderSide: BorderSide.none,
        ),
        contentPadding: EdgeInsets.symmetric(vertical: 0),
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: Colors.grey[200],
        child: Icon(icon, color: Colors.black),
      ),
      title: Text(label),
      onTap: onTap,
    );
  }

  Widget _buildContactItem(Map<String, String> contact) {
    return ListTile(
      leading: CircleAvatar(
        backgroundImage: AssetImage(contact['image']!),
      ),
      title: Text(contact['name']!),
      onTap: () {
        // Action: démarrer discussion
      },
    );
  }
}
