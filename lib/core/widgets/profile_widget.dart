import 'package:flutter/material.dart';

class CustomDrawer extends StatelessWidget {
  const CustomDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    return Drawer(
      backgroundColor: Colors.white,
      child: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  // _buildProfileHeader(context),
                  const Divider(height: 1),
                  _buildTabMenu(),
                  const Divider(height: 1),
                  _buildUserInfos(),
                  const Divider(height: 16),
                  _buildExperienceSection(),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: ElevatedButton.icon(
                onPressed: () {
                  // action déconnexion
                },
                icon: const Icon(Icons.logout),
                label: const Text('Se déconnecter'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red,
                  foregroundColor: Colors.white,
                  minimumSize: const Size.fromHeight(48),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // Widget _buildProfileHeader(BuildContext context) {
  //   return Container(
  //     decoration: const BoxDecoration(
  //       gradient: LinearGradient(
  //         colors: [Color(0xFFB16CEA), Color(0xFFFF7E5F)],
  //         begin: Alignment.topLeft,
  //         end: Alignment.bottomRight,
  //       ),
  //     ),
  //     padding: const EdgeInsets.only(top: 60, bottom: 20),
  //     child: Column(
  //       children: [
  //         const CircleAvatar(
  //           radius: 40,
  //           backgroundImage: AssetImage('assets/images/home/user1.png'),
  //         ),
  //         const SizedBox(height: 12),
  //         const Text(
  //           'Aby Diop',
  //           style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
  //         ),
  //         const Text(
  //           'Etudiant en génie logiciel à UCAD\nDakar - Sénégal',
  //           textAlign: TextAlign.center,
  //           style: TextStyle(color: Colors.white70, fontSize: 14),
  //         ),
  //         const SizedBox(height: 8),
  //         Row(
  //           mainAxisAlignment: MainAxisAlignment.center,
  //           children: [
  //             Stack(
  //               children: [
  //                 Positioned(left: 0, child: _relationAvatar('assets/images/home/user2.png')),
  //                 Positioned(left: 16, child: _relationAvatar('assets/images/home/user3.png')),
  //                 Positioned(left: 32, child: _relationAvatar('assets/images/home/user4.png')),
  //               ],
  //             ),
  //             const SizedBox(width: 48),
  //             const Text(
  //               '5435 relations',
  //               style: TextStyle(color: Colors.white),
  //             ),
  //           ],
  //         ),
  //         const SizedBox(height: 12),
  //         Row(
  //           mainAxisAlignment: MainAxisAlignment.center,
  //           children: [
  //             _drawerButton('Ajouter', filled: true),
  //             const SizedBox(width: 8),
  //             _drawerButton('Message', filled: false),
  //           ],
  //         ),
  //       ],
  //     ),
  //   );
  // }

  static Widget _relationAvatar(String path) {
    return CircleAvatar(
      backgroundImage: AssetImage(path),
      radius: 12,
    );
  }

  static Widget _drawerButton(String text, {required bool filled}) {
    return OutlinedButton(
      onPressed: () {},
      style: OutlinedButton.styleFrom(
        backgroundColor: filled ? Colors.white : Colors.transparent,
        side: const BorderSide(color: Colors.white),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: filled ? Colors.blue : Colors.white,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  Widget _buildTabMenu() {
    return Container(
      height: 50,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: const [
          _TabItem(label: 'Infos', icon: Icons.info, selected: true),
          _TabItem(label: 'Activités', icon: Icons.bar_chart),
          _TabItem(label: 'Membres', icon: Icons.group),
        ],
      ),
    );
  }

  Widget _buildUserInfos() {
    return const Padding(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.location_on, size: 18),
              SizedBox(width: 8),
              Text('Dakar Sénégal'),
            ],
          ),
          SizedBox(height: 8),
          Row(
            children: [
              Icon(Icons.school, size: 18),
              SizedBox(width: 8),
              Text('Université (Etablissement scolaire)'),
            ],
          ),
          SizedBox(height: 16),
          Text(
            'À propos de moi',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 4),
          Text(
            'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt...',
            style: TextStyle(fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildExperienceSection() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Expérience', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          _experienceItem(
            logo: 'assets/images/home/user2.png',
            title: 'Développeuse Mobile - iOS/Android',
            company: 'Chez Dyson - France',
            duration: 'De Avril 2023 - Aujourd’hui (3 ans)',
            tag: 'Freelance',
          ),
          const SizedBox(height: 12),
          _experienceItem(
            logo: 'assets/images/home/user1.png',
            title: 'Developpeuse Backend',
            company: 'Chez Idilla - Dakar',
            duration: 'De Avril 2023 - Aujourd’hui (3 ans)',
            tag: 'Alternance',
          ),
          const SizedBox(height: 12),
          _experienceItem(
            logo: 'assets/images/home/user3.png',
            title: 'Architecte logicielle',
            company: 'Chez BMW - Dakar',
            duration: 'De Avril 2023 - Aujourd’hui (3 ans)',
            tag: 'Stagiaire',
          ),
        ],
      ),
    );
  }

  Widget _experienceItem({
    required String logo,
    required String title,
    required String company,
    required String duration,
    required String tag,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CircleAvatar(backgroundImage: AssetImage(logo), radius: 20),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
              Text(company, style: const TextStyle(color: Colors.grey)),
              Text(duration, style: const TextStyle(color: Colors.grey, fontSize: 13)),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.grey.shade200,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(tag, style: const TextStyle(fontSize: 12)),
              )
            ],
          ),
        )
      ],
    );
  }
}

class _TabItem extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool selected;

  const _TabItem({
    required this.label,
    required this.icon,
    this.selected = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, color: selected ? Colors.blue : Colors.grey, size: 20),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: selected ? Colors.blue : Colors.grey,
            fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
          ),
        ),
      ],
    );
  }
}
